import asyncio
import aiohttp
import json
import logging
import time
import sqlite3
import re
import os
import sys
from typing import List, Dict, Optional, Any
from concurrent.futures import ThreadPoolExecutor
import requests

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class AmazonScraper:
    """
    Amazon 产品数据采集器（使用 ScraperAPI）

    功能特性：
    1. 智能关键词搜索，支持销量阈值自动停止
    2. 自动检测并跳过已下载的关键词，避免重复调用 API
    3. 本地 SQLite 缓存，记录所有下载历史

    重复下载检查机制：
    - has_keyword_been_downloaded(): 检查关键词是否已下载
    - get_keyword_download_info(): 获取下载时间和记录数
    - 在 search_keyword_with_smart_stop() 中自动跳过已下载的关键词

    注意：此检查机制可复用于其他 API（如 APIFY_API）：
    1. 在数据库中记录 API 类型和下载时间
    2. 在调用 API 前检查是否已有缓存数据
    3. 如有缓存则直接返回，避免重复调用
    """
    def __init__(
        self,
        api_key: str,
        db_path: str = "data/scraper_results.db",
        max_concurrent: int = 10,  # 最大并发请求数
        request_timeout: int = 30,  # 请求超时时间（秒）
        max_retries: int = 5,  # 增加到5次重试
        retry_backoff_base: float = 2.0,  # 增加基础延迟
        retry_backoff_max: float = 60.0,  # 增加最大延迟
    ):
        self.api_key = api_key
        self.base_url = "http://api.scraperapi.com"
        self.db_path = db_path
        self.max_concurrent = max_concurrent
        self.request_timeout = request_timeout
        self.max_retries = max_retries
        self.retry_backoff_base = retry_backoff_base
        self.retry_backoff_max = retry_backoff_max
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS scrape_results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    result_type TEXT NOT NULL,
                    asin TEXT,
                    search_query TEXT,
                    country_code TEXT,
                    data_json TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT (datetime('now'))
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_scrape_results_asin ON scrape_results(asin)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_scrape_results_search_query ON scrape_results(search_query)"
            )

    def _get_retry_delay(self, retry_after: Optional[str], attempt: int) -> float:
        if retry_after:
            try:
                return min(float(retry_after), self.retry_backoff_max)
            except ValueError:
                pass
        delay = self.retry_backoff_base * (2 ** attempt)
        return min(delay, self.retry_backoff_max)

    async def _request_json_async(
        self,
        session: aiohttp.ClientSession,
        params: Dict[str, Any],
        context: str,
    ) -> Optional[Dict[str, Any]]:
        for attempt in range(self.max_retries + 1):
            try:
                async with session.get(
                    self.base_url,
                    params=params,
                    timeout=aiohttp.ClientTimeout(total=self.request_timeout)
                ) as response:
                    status = response.status
                    if status == 200:
                        try:
                            return await response.json(content_type=None)
                        except Exception as e:
                            body = await response.text()
                            logging.error(f"{context} JSON decode failed: {e}. Body: {body[:200]}")
                            return None

                    if status in (429, 500, 502, 503, 504):
                        delay = self._get_retry_delay(response.headers.get("Retry-After"), attempt)
                        if attempt < self.max_retries:
                            logging.warning(
                                f"{context} got {status}, retrying in {delay:.1f}s "
                                f"(attempt {attempt + 1}/{self.max_retries})"
                            )
                            await asyncio.sleep(delay)
                            continue
                        logging.error(f"{context} failed with status {status} after retries")
                        return None

                    body = await response.text()
                    logging.error(f"{context} failed with status {status}. Body: {body[:200]}")
                    return None

            except asyncio.TimeoutError:
                delay = self._get_retry_delay(None, attempt)
                if attempt < self.max_retries:
                    logging.warning(
                        f"{context} timed out, retrying in {delay:.1f}s "
                        f"(attempt {attempt + 1}/{self.max_retries})"
                    )
                    await asyncio.sleep(delay)
                    continue
                logging.error(f"{context} timed out after retries")
                return None
            except Exception as e:
                delay = self._get_retry_delay(None, attempt)
                if attempt < self.max_retries:
                    logging.warning(
                        f"{context} error: {e}, retrying in {delay:.1f}s "
                        f"(attempt {attempt + 1}/{self.max_retries})"
                    )
                    await asyncio.sleep(delay)
                    continue
                logging.error(f"{context} failed after retries: {e}")
                return None
        return None

    def _save_result(self, result_type, data, asin=None, search_query=None, country_code=None):
        if data is None:
            return
        try:
            payload_json = json.dumps(data, ensure_ascii=False)
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    """
                    INSERT INTO scrape_results (
                        result_type,
                        asin,
                        search_query,
                        country_code,
                        data_json
                    ) VALUES (?, ?, ?, ?, ?)
                    """,
                    (result_type, asin, search_query, country_code, payload_json),
                )
        except sqlite3.Error as e:
            logging.error(f"保存到数据库失败: {e}")

    def _load_latest_result(self, result_type, asin=None, search_query=None, country_code=None):
        sql = "SELECT data_json FROM scrape_results WHERE result_type = ?"
        params = [result_type]
        if asin:
            sql += " AND asin = ?"
            params.append(asin)
        if search_query:
            sql += " AND search_query = ?"
            params.append(search_query)
        if country_code:
            sql += " AND country_code = ?"
            params.append(country_code)
        sql += " ORDER BY created_at DESC, id DESC LIMIT 1"
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(sql, params).fetchone()
        if not row:
            return None
        return json.loads(row[0])

    def load_latest_product(self, asin, country_code='us'):
        return self._load_latest_result("product", asin=asin, country_code=country_code)

    def load_latest_search(self, query, country_code='us'):
        return self._load_latest_result("search", search_query=query, country_code=country_code)

    def has_keyword_been_downloaded(self, keyword: str, country_code: str = 'us') -> bool:
        """
        检查关键词是否已经下载过

        Args:
            keyword: 搜索关键词
            country_code: 国家代码

        Returns:
            True 如果已下载，False 如果未下载
        """
        sql = """
            SELECT COUNT(*) FROM scrape_results
            WHERE result_type = 'search'
            AND search_query = ?
            AND country_code = ?
        """
        with sqlite3.connect(self.db_path) as conn:
            count = conn.execute(sql, [keyword, country_code]).fetchone()[0]
        return count > 0

    def get_keyword_download_info(self, keyword: str, country_code: str = 'us') -> dict:
        """
        获取关键词的下载信息

        Args:
            keyword: 搜索关键词
            country_code: 国家代码

        Returns:
            包含下载时间和记录数的字典，如果未下载则返回 None
        """
        sql = """
            SELECT created_at, COUNT(*) as record_count
            FROM scrape_results
            WHERE result_type = 'search'
            AND search_query = ?
            AND country_code = ?
            GROUP BY search_query
            ORDER BY created_at DESC
            LIMIT 1
        """
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(sql, [keyword, country_code]).fetchone()

        if row:
            return {
                'downloaded_at': row[0],
                'record_count': row[1],
                'keyword': keyword,
                'country_code': country_code
            }
        return None

    def scrape_product(self, asin, country_code='us'):
        """
        使用 ScraperAPI 获取亚马逊产品详情 (使用 autoparse=true 自动解析 JSON)
        """
        url = f"https://www.amazon.{country_code}/dp/{asin}" if country_code == 'us' or country_code == 'com' else f"https://www.amazon.{country_code}/dp/{asin}"
        # 修正: 上面的 url 逻辑可以简化，如果你需要更通用的逻辑可以调整
        # 对于 com 站点通常是 amazon.com
        if country_code == 'us':
            domain = 'com'
        else:
            domain = country_code
            
        target_url = f"https://www.amazon.{domain}/dp/{asin}"
        
        payload = {
            'api_key': self.api_key,
            'url': target_url,
            'autoparse': 'true', # 关键参数：让 ScraperAPI 自动解析返回 JSON
            'country_code': country_code
        }

        try:
            logging.info(f"正在抓取产品: {asin} ({domain})...")
            start_time = time.time()
            response = requests.get(self.base_url, params=payload)
            end_time = time.time()
            duration = end_time - start_time
            logging.info(f"抓取完成，耗时: {duration:.2f} 秒")
            response.raise_for_status() # 检查请求是否成功
            
            # ScraperAPI autoparse=true 返回 JSON
            data = response.json()
            self._save_result(
                "product",
                data,
                asin=asin,
                country_code=country_code,
            )
            return data
            
        except requests.exceptions.RequestException as e:
            logging.error(f"抓取失败: {e}")
            return None

    def search_products(self, query, country_code='us', max_pages=1):
        """
        搜索亚马逊产品 (使用 autoparse=true)，支持获取多页结果
        """
        if country_code == 'us':
            domain = 'com'
        else:
            domain = country_code
            
        all_results = []
        combined_data = None

        for page in range(1, max_pages + 1):
            target_url = f"https://www.amazon.{domain}/s?k={query}"
            if page > 1:
                target_url += f"&page={page}"
            
            payload = {
                'api_key': self.api_key,
                'url': target_url,
                'autoparse': 'true',
                'country_code': country_code
            }

            try:
                logging.info(f"正在搜索: {query} ({domain}), 第 {page}/{max_pages} 页...")
                start_time = time.time()
                response = requests.get(self.base_url, params=payload)
                end_time = time.time()
                duration = end_time - start_time
                logging.info(f"第 {page} 页搜索完成，耗时: {duration:.2f} 秒")
                response.raise_for_status()
                
                data = response.json()
                if combined_data is None:
                    combined_data = data

                page_results = data.get('results', [])
                # Add page number to each result
                for result in page_results:
                    result['page'] = page
                all_results.extend(page_results)
                
                # 如果当前页没有结果，可能已经到最后一页了
                if not page_results:
                    logging.info(f"第 {page} 页没有更多结果，停止翻页。")
                    break
                    
            except requests.exceptions.RequestException as e:
                logging.error(f"第 {page} 页搜索失败: {e}")
                break
        
        if combined_data:
            combined_data['results'] = all_results
            self._save_result(
                "search",
                combined_data,
                search_query=query,
                country_code=country_code,
            )
            return combined_data
        return None

    # ========== 异步并发抓取方法 ==========

    async def _scrape_product_async(
        self,
        session: aiohttp.ClientSession,
        asin: str,
        country_code: str = 'us',
        semaphore: Optional[asyncio.Semaphore] = None
    ) -> Optional[Dict[str, Any]]:
        """
        异步抓取单个产品详情
        """
        if semaphore:
            async with semaphore:
                return await self._fetch_product(session, asin, country_code)
        return await self._fetch_product(session, asin, country_code)

    async def _fetch_product(
        self,
        session: aiohttp.ClientSession,
        asin: str,
        country_code: str
    ) -> Optional[Dict[str, Any]]:
        """
        执行实际的异步请求
        """
        domain = 'com' if country_code == 'us' else country_code
        target_url = f"https://www.amazon.{domain}/dp/{asin}"

        params = {
            'api_key': self.api_key,
            'url': target_url,
            'autoparse': 'true',
            'country_code': country_code
        }

        try:
            logging.info(f"正在异步抓取产品: {asin} ({domain})...")
            start_time = time.time()

            data = await self._request_json_async(session, params, f"Product {asin}")
            if data is None:
                return None

            end_time = time.time()
            duration = end_time - start_time
            logging.info(f"产品 {asin} 抓取完成，耗时: {duration:.2f} 秒")

            self._save_result(
                "product",
                data,
                asin=asin,
                country_code=country_code,
            )
            return data

        except asyncio.TimeoutError:
            logging.error(f"产品 {asin} 抓取超时")
            return None
        except Exception as e:
            logging.error(f"产品 {asin} 抓取失败: {e}")
            return None

    async def scrape_products_batch_async(
        self,
        asins: List[str],
        country_code: str = 'us',
        show_progress: bool = True
    ) -> List[Optional[Dict[str, Any]]]:
        """
        异步批量抓取多个产品详情（并发执行，失败自动重试）

        Args:
            asins: ASIN 列表
            country_code: 国家代码
            show_progress: 是否显示进度

        Returns:
            产品详情列表（与输入 asins 顺序对应）
        """
        semaphore = asyncio.Semaphore(self.max_concurrent)

        async with aiohttp.ClientSession() as session:
            tasks = []
            for asin in asins:
                task = self._scrape_product_async(session, asin, country_code, semaphore)
                tasks.append(task)

            if show_progress:
                logging.info(f"开始批量抓取 {len(asins)} 个产品（并发数: {self.max_concurrent}）...")

            # 第一轮：并发执行所有任务
            results = await asyncio.gather(*tasks)

            # 统计失败的产品
            failed_indices = [i for i, r in enumerate(results) if r is None]

            if failed_indices and show_progress:
                logging.warning(f"第一轮抓取: 成功 {len(asins) - len(failed_indices)}/{len(asins)}，准备重试失败的 {len(failed_indices)} 个产品...")

            # 第二轮：对失败的产品进行重试（降低并发数）
            if failed_indices:
                retry_semaphore = asyncio.Semaphore(max(3, self.max_concurrent // 3))  # 降低并发
                retry_tasks = []

                for idx in failed_indices:
                    asin = asins[idx]
                    task = self._scrape_product_async(session, asin, country_code, retry_semaphore)
                    retry_tasks.append((idx, task))

                # 执行重试
                for idx, task in retry_tasks:
                    result = await task
                    if result is not None:
                        results[idx] = result

                # 第三轮：对仍然失败的产品进行最后重试（串行）
                still_failed = [i for i in failed_indices if results[i] is None]
                if still_failed and show_progress:
                    logging.warning(f"第二轮抓取: 仍有 {len(still_failed)} 个产品失败，进行最后重试（串行）...")

                for idx in still_failed:
                    asin = asins[idx]
                    await asyncio.sleep(3)  # 串行重试，增加延迟
                    result = await self._fetch_product(session, asin, country_code)
                    if result is not None:
                        results[idx] = result

            if show_progress:
                success_count = sum(1 for r in results if r is not None)
                logging.info(f"批量抓取完成: 成功 {success_count}/{len(asins)}")

            return results

    def scrape_products_batch(
        self,
        asins: List[str],
        country_code: str = 'us',
        show_progress: bool = True
    ) -> List[Optional[Dict[str, Any]]]:
        """
        同步包装器：批量抓取多个产品（内部使用异步并发）

        Args:
            asins: ASIN 列表
            country_code: 国家代码
            show_progress: 是否显示进度

        Returns:
            产品详情列表
        """
        return asyncio.run(self.scrape_products_batch_async(asins, country_code, show_progress))

    async def search_products_multiple_queries_async(
        self,
        queries: List[str],
        country_code: str = 'us',
        max_pages: int = 1,
        show_progress: bool = True
    ) -> Dict[str, Optional[Dict[str, Any]]]:
        """
        异步并发搜索多个关键词

        Args:
            queries: 关键词列表
            country_code: 国家代码
            max_pages: 每个关键词最多抓取页数
            show_progress: 是否显示进度

        Returns:
            字典 {query: search_results}
        """
        semaphore = asyncio.Semaphore(self.max_concurrent)

        async with aiohttp.ClientSession() as session:
            results = {}

            if show_progress:
                logging.info(f"开始搜索 {len(queries)} 个关键词（并发数: {self.max_concurrent}）...")

            tasks = []
            for query in queries:
                task = self._search_single_query_async(
                    session, query, country_code, max_pages, semaphore
                )
                tasks.append((query, task))

            # 并发执行所有搜索
            for query, task in tasks:
                results[query] = await task

            if show_progress:
                success_count = sum(1 for r in results.values() if r is not None)
                logging.info(f"多关键词搜索完成: 成功 {success_count}/{len(queries)}")

            return results

    async def _search_single_query_async(
        self,
        session: aiohttp.ClientSession,
        query: str,
        country_code: str,
        max_pages: int,
        semaphore: asyncio.Semaphore
    ) -> Optional[Dict[str, Any]]:
        """
        异步搜索单个关键词（支持多页）
        """
        if semaphore:
            async with semaphore:
                return await self._fetch_search_pages(session, query, country_code, max_pages)
        return await self._fetch_search_pages(session, query, country_code, max_pages)

    async def _fetch_search_pages(
        self,
        session: aiohttp.ClientSession,
        query: str,
        country_code: str,
        max_pages: int
    ) -> Optional[Dict[str, Any]]:
        """
        异步抓取搜索结果的多个页面
        """
        domain = 'com' if country_code == 'us' else country_code
        all_results = []
        combined_data = None

        for page in range(1, max_pages + 1):
            target_url = f"https://www.amazon.{domain}/s?k={query}"
            if page > 1:
                target_url += f"&page={page}"

            params = {
                'api_key': self.api_key,
                'url': target_url,
                'autoparse': 'true',
                'country_code': country_code
            }

            try:
                logging.info(f"正在异步搜索: {query} ({domain}), 第 {page}/{max_pages} 页...")
                start_time = time.time()

                data = await self._request_json_async(session, params, f"Search {query} page {page}")
                if data is None:
                    break

                end_time = time.time()
                duration = end_time - start_time
                logging.info(f"关键词 '{query}' 第 {page} 页搜索完成，耗时: {duration:.2f} 秒")

                if combined_data is None:
                    combined_data = data

                page_results = data.get('results', [])
                # Add page number to each result
                for result in page_results:
                    result['page'] = page
                all_results.extend(page_results)

                if not page_results:
                    logging.info(f"关键词 '{query}' 第 {page} 页没有更多结果，停止翻页。")
                    break

            except asyncio.TimeoutError:
                logging.error(f"关键词 '{query}' 第 {page} 页搜索超时")
                break
            except Exception as e:
                logging.error(f"关键词 '{query}' 第 {page} 页搜索失败: {e}")
                break

        if combined_data:
            combined_data['results'] = all_results
            self._save_result(
                "search",
                combined_data,
                search_query=query,
                country_code=country_code,
            )
            return combined_data

        return None

    def search_products_multiple_queries(
        self,
        queries: List[str],
        country_code: str = 'us',
        max_pages: int = 1,
        show_progress: bool = True
    ) -> Dict[str, Optional[Dict[str, Any]]]:
        """
        同步包装器：搜索多个关键词（内部使用异步并发）

        Args:
            queries: 关键词列表
            country_code: 国家代码
            max_pages: 每个关键词最多抓取页数
            show_progress: 是否显示进度

        Returns:
            字典 {query: search_results}
        """
        return asyncio.run(
            self.search_products_multiple_queries_async(queries, country_code, max_pages, show_progress)
        )

    # ========== 智能关键词搜索（带销量停止条件）==========

    @staticmethod
    def _parse_purchase_count(purchase_history_message: Optional[str]) -> Optional[int]:
        """
        从 purchase_history_message 中提取购买数量

        示例:
            "2K+ bought in past month" -> 2000
            "1K+ bought in past month" -> 1000
            "300+ bought in past month" -> 300
            "50+ bought in past month" -> 50
            "5+ bought in past month" -> 5
            None -> None

        Args:
            purchase_history_message: 购买历史消息

        Returns:
            提取的数量，如果无法解析则返回 None
        """
        if not purchase_history_message:
            return None

        # 匹配模式: "数字+单位" 或 "数字+"
        # 例如: "2K+", "300+", "1K+"
        pattern = r'(\d+(?:\.\d+)?)\s*([KkMm])?\s*\+'
        match = re.search(pattern, purchase_history_message)

        if not match:
            return None

        number = float(match.group(1))
        unit = match.group(2)

        # 转换单位
        if unit:
            unit = unit.upper()
            if unit == 'K':
                number *= 1000
            elif unit == 'M':
                number *= 1000000

        return int(number)

    def _check_page_low_sales(
        self,
        page_results: List[Dict[str, Any]],
        threshold: int = 10
    ) -> bool:
        """
        检查当前页面是否所有商品销量都低于阈值

        Args:
            page_results: 当前页面的搜索结果列表
            threshold: 销量阈值（默认10，即个位数）

        Returns:
            如果所有商品销量都低于阈值，返回 True
        """
        if not page_results:
            return True

        # 统计有销量信息的商品数量
        products_with_sales = 0
        low_sales_count = 0

        # 检查每个商品的销量
        for product in page_results:
            purchase_msg = product.get('purchase_history_message')
            count = self._parse_purchase_count(purchase_msg)

            # 如果有销量信息
            if count is not None:
                products_with_sales += 1
                if count < threshold:
                    low_sales_count += 1
                else:
                    # 有商品销量 >= 阈值，返回 False
                    return False

        # 如果没有任何商品有销量信息，继续抓取（返回False）
        if products_with_sales == 0:
            return False

        # 所有有销量信息的商品都低于阈值
        return low_sales_count == products_with_sales

    def search_keyword_with_smart_stop(
        self,
        keyword: str,
        country_code: str = 'us',
        max_pages: int = 100,
        sales_threshold: int = 10,
        fetch_product_details: bool = False,
        show_progress: bool = True
    ) -> Dict[str, Any]:
        """
        智能关键词搜索：自动抓取所有相关ASIN，当页面销量都低于阈值时停止

        Args:
            keyword: 搜索关键词
            country_code: 国家代码
            max_pages: 最大页数限制（默认100）
            sales_threshold: 销量阈值，当页面所有商品销量都低于此值时停止（默认10）
            fetch_product_details: 是否抓取每个ASIN的详细产品信息（默认False）
            show_progress: 是否显示进度

        Returns:
            包含搜索结果和产品详情的字典
        """
        # 检查关键词是否已经下载过
        if self.has_keyword_been_downloaded(keyword, country_code):
            download_info = self.get_keyword_download_info(keyword, country_code)
            logging.info(
                f"关键词 '{keyword}' 已在 {download_info['downloaded_at']} 下载过 "
                f"({download_info['record_count']} 条记录)，跳过重复下载"
            )

            # 从缓存加载已有数据
            cached_data = self.load_latest_search(keyword, country_code)
            if cached_data:
                return {
                    'search_results': cached_data.get('search_results', []),
                    'product_details': [],
                    'pages_scraped': cached_data.get('pages_scraped', 0),
                    'total_asins': cached_data.get('total_asins', 0),
                    'stopped_reason': f"使用缓存数据 (下载于 {download_info['downloaded_at']})",
                    'from_cache': True
                }

        if country_code == 'us':
            domain = 'com'
        else:
            domain = country_code

        all_search_results = []
        all_asins = []
        stopped_reason = None
        pages_scraped = 0

        logging.info(f"开始智能搜索关键词: '{keyword}' (最大{max_pages}页, 销量阈值<{sales_threshold})")

        # 第一阶段：搜索并收集所有ASIN
        for page in range(1, max_pages + 1):
            target_url = f"https://www.amazon.{domain}/s?k={keyword}"
            if page > 1:
                target_url += f"&page={page}"

            payload = {
                'api_key': self.api_key,
                'url': target_url,
                'autoparse': 'true',
                'country_code': country_code
            }

            try:
                if show_progress:
                    logging.info(f"正在搜索第 {page} 页...")

                start_time = time.time()
                response = requests.get(self.base_url, params=payload, timeout=self.request_timeout)
                end_time = time.time()
                duration = end_time - start_time

                response.raise_for_status()
                data = response.json()

                page_results = data.get('results', [])

                if not page_results:
                    stopped_reason = f"第 {page} 页没有更多结果"
                    logging.info(stopped_reason)
                    break

                # Add page number to each result
                for result in page_results:
                    result['page'] = page

                # 保存搜索结果
                all_search_results.extend(page_results)

                # 提取ASIN
                page_asins = [item.get('asin') for item in page_results if item.get('asin')]
                all_asins.extend(page_asins)

                pages_scraped = page

                if show_progress:
                    logging.info(f"第 {page} 页完成，耗时: {duration:.2f}秒，找到 {len(page_asins)} 个产品")

                # 检查销量停止条件
                if page >= 1 and self._check_page_low_sales(page_results, sales_threshold):
                    stopped_reason = f"第 {page} 页所有商品销量都低于 {sales_threshold}，停止抓取"
                    logging.info(stopped_reason)
                    break

            except requests.exceptions.RequestException as e:
                stopped_reason = f"第 {page} 页请求失败: {e}"
                logging.error(stopped_reason)
                break

        # 保存搜索结果到数据库
        combined_search_data = {
            'keyword': keyword,
            'results': all_search_results,
            'total_results': len(all_search_results),
            'pages_scraped': pages_scraped,
            'stopped_reason': stopped_reason
        }
        self._save_result(
            "keyword_search",
            combined_search_data,
            search_query=keyword,
            country_code=country_code
        )

        logging.info(f"搜索完成: 共抓取 {pages_scraped} 页，找到 {len(all_asins)} 个ASIN")

        # 第二阶段：批量抓取产品详情（如果需要）
        product_details = []
        if fetch_product_details and all_asins:
            logging.info(f"开始批量抓取 {len(all_asins)} 个产品的详细信息...")
            product_details = self.scrape_products_batch(
                all_asins,
                country_code=country_code,
                show_progress=show_progress
            )
            logging.info(f"产品详情抓取完成")

        # 返回完整结果
        result = {
            'keyword': keyword,
            'country_code': country_code,
            'pages_scraped': pages_scraped,
            'stopped_reason': stopped_reason,
            'total_asins': len(all_asins),
            'search_results': all_search_results,
            'asins': all_asins,
            'product_details': product_details if fetch_product_details else None
        }

        return result


if __name__ == "__main__":
    # 请替换为你的 ScraperAPI Key
    # 注册地址: https://www.scraperapi.com
    API_KEY = os.environ.get('SCRAPERAPI_KEY', 'YOUR_SCRAPERAPI_KEY_HERE')

    if API_KEY == "YOUR_SCRAPERAPI_KEY_HERE":
        print("错误: 请先设置你的 ScraperAPI Key")
        print("方法1: 设置环境变量 SCRAPERAPI_KEY")
        print("方法2: 在代码中直接修改 API_KEY 变量")
        sys.exit(1)
    else:
        # 初始化爬虫，设置并发数为 10
        scraper = AmazonScraper(API_KEY, max_concurrent=10)

        # 创建输出文件
        output_file = f"scraper_output_{time.strftime('%Y%m%d_%H%M%S')}.json"
        all_output = {}

        # ========== 示例 1: 单个关键词搜索（同步）==========
        print("\n=== 示例 1: 单个关键词搜索 ===")
        search_results = scraper.search_products("camping", max_pages=1)
        if search_results:
            print("\n完整搜索结果:")
            print(json.dumps(search_results, indent=2, ensure_ascii=False))
            results_list = search_results.get('results', [])
            print(f"\n找到 {len(results_list)} 个产品")
            all_output['example_1_search'] = search_results

        # ========== 示例 2: 单个产品详情抓取（同步）==========
        if search_results and len(results_list) > 0:
            first_asin = results_list[0]['asin']
            print(f"\n=== 示例 2: 单个产品详情抓取 ({first_asin}) ===")
            product_details = scraper.scrape_product(first_asin)
            if product_details:
                print("\n完整产品详情:")
                print(json.dumps(product_details, indent=2, ensure_ascii=False))
                all_output['example_2_product_details'] = product_details

        # ========== 示例 3: 批量产品详情抓取（并发）⚡ ==========
        print("\n=== 示例 3: 批量产品详情抓取（并发）⚡ ===")
        asins = ["B0D2KF98MC", "B08L5VPX9C", "B07ZPKBL9V"]  # 示例 ASIN
        batch_results = scraper.scrape_products_batch(asins, show_progress=True)
        print(f"\n批量抓取完成: {len(batch_results)} 个产品")
        for i, result in enumerate(batch_results):
            if result:
                print(f"\n[{i+1}] 产品完整信息:")
                print(json.dumps(result, indent=2, ensure_ascii=False))
        all_output['example_3_batch_products'] = batch_results

        # ========== 示例 4: 多关键词搜索（并发）⚡ ==========
        print("\n=== 示例 4: 多关键词搜索（并发）⚡ ===")
        queries = ["camping gear", "hiking boots", "outdoor jacket"]
        multi_search_results = scraper.search_products_multiple_queries(
            queries,
            max_pages=1,
            show_progress=True
        )
        print(f"\n多关键词搜索完成:")
        for query, results in multi_search_results.items():
            if results:
                count = len(results.get('results', []))
                print(f"\n关键词 '{query}': {count} 个产品")
                print("完整搜索结果:")
                print(json.dumps(results, indent=2, ensure_ascii=False))
        all_output['example_4_multi_search'] = multi_search_results

        # 保存所有结果到文件
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(all_output, f, indent=2, ensure_ascii=False)
        print(f"\n\n所有结果已保存到文件: {output_file}")
