// ========================================
// 卖家精灵数据批量导出自动化脚本
// ========================================
// 功能说明：
// 1. 自动连接Chrome浏览器并打开Amazon搜索页面
// 2. 自动点击卖家精灵按钮并加载数据
// 3. 自动加载所有数据（点击"加载更多"直到没有更多数据）
// 4. 分批导出数据（每批最多100条），导出后删除
// ========================================

// 导入所需的Node.js模块
const puppeteer = require('puppeteer');  // 浏览器自动化工具
const fs = require('fs');                // 文件系统模块，用于创建文件夹
const path = require('path');            // 路径处理模块
const XLSX = require('xlsx');            // Excel文件读取模块

// ================= 配置区域 =================
// 从环境变量SS_KEYWORD读取搜索关键词，如果没有则默认使用'camping'
const KEYWORD = process.env.SS_KEYWORD || 'camping';
// Chrome远程调试地址，用于连接已打开的Chrome浏览器
const CDP_URL = 'http://127.0.0.1:9222';
// 用户操作超时时间（毫秒），2分钟（减少超时时间，避免长时间卡住）
const USER_WAIT_TIMEOUT = 120000;
// 稳定等待时间（秒），用于等待数据稳定
const STABLE_WAIT_TIME = 60;
// 批次大小，每次导出的数据条数
const BATCH_SIZE = 100;
// ============================================

// 倒计时函数：显示剩余秒数的进度条
// seconds: 倒计时秒数
// prefix: 显示在倒计时前面的文字
async function countDown(seconds, prefix = '') {
    // 从秒数倒序循环到1
    for (let i = seconds; i > 0; i--) {
        // 在同一行显示倒计时，使用\r回到行首
        process.stdout.write(`\r${prefix}: 剩余 ${i} 秒...    `);
        // 等待1秒
        await new Promise(r => setTimeout(r, 1000));
    }
    // 清除倒计时显示
    process.stdout.write('\r' + ' '.repeat(60) + '\r');
}

// ==================== 主程序开始 ====================
// 使用立即执行函数(IIFE)来运行异步代码
(async () => {
    // 声明浏览器变量
    let browser;
    // 导出成功标志（用于决定是否关闭浏览器）
    let exportSuccess = false;
    try {
        // ===== 步骤1: 连接Chrome浏览器 =====
        console.log(`[1/3] 连接 Chrome (端口 9222)...`);
        // 通过CDP(Chrome DevTools Protocol)连接到已打开的Chrome
        browser = await puppeteer.connect({ browserURL: CDP_URL, defaultViewport: null });
        console.log('[√] 已连接。');

        // 获取浏览器中所有已打开的标签页
        let pages = await browser.pages();
        // 查找是否已经有Amazon搜索页面
        let page = pages.find(p => p.url().includes('amazon.com/s'));
        // 如果没有找到Amazon页面
        if (!page) {
            // 创建一个新的标签页
            page = await browser.newPage();
        } else {
            // 如果找到了，就把该标签页置顶
            await page.bringToFront();
        }

        // 无论是新页面还是已有页面，都导航到新的搜索关键词
        console.log(`[*] 正在导航到搜索页面: ${KEYWORD}`);
        try {
            await page.goto(`https://www.amazon.com/s?k=${KEYWORD}`, {
                waitUntil: 'domcontentloaded',
                timeout: 30000  // 30秒超时
            });
            console.log(`[√] 页面加载完成`);
        } catch (err) {
            console.log(`[!] 页面加载超时或失败: ${err.message}`);
            console.log(`[*] 尝试继续执行...`);
        }

        // 等待15秒让卖家精灵扩展加载
        console.log(`[*] 等待卖家精灵扩展加载 (15秒)...`);
        await countDown(15, '[*] 等待卖家精灵扩展加载');
        console.log(`[√] 等待完成`);



        // 设置下载路径为 output/sellerspirit/{关键词} 文件夹
        const downloadPath = path.resolve(process.cwd(), 'output', 'sellerspirit', KEYWORD);
        // 如果文件夹不存在，就创建它（recursive表示可以创建多级目录）
        if (!fs.existsSync(downloadPath)) fs.mkdirSync(downloadPath, { recursive: true });
        // 创建CDP会话，用于设置下载行为
        const client = await browser.target().createCDPSession();
        // 告诉Chrome允许下载，并设置下载路径
        await client.send('Browser.setDownloadBehavior', {
            behavior: 'allow', downloadPath: downloadPath, eventsEnabled: true
        });

        // 等待页面稳定（避免detached frame错误）
        console.log('[*] 等待页面稳定...');
        await new Promise(r => setTimeout(r, 2000));

        // 重新获取页面对象，确保使用最新的page引用
        const allPages = await browser.pages();
        page = allPages.find(p => p.url().includes('amazon.com')) || allPages[0];

        // ===== 步骤2: 检查卖家精灵是否已打开 =====
        // 通过多种方式检测卖家精灵面板是否已经显示
        const hasSellerSpirit = await page.evaluate(() => {
            const text = document.body.innerText || '';

            // 方法1: 检测特征文字
            const hasCharacteristicText =
                text.includes('总销量') ||
                text.includes('总销售额') ||
                text.includes('平均销量') ||
                text.includes('导出明细') ||
                /当前页\s*\d+\s*个商品/.test(text);

            // 方法2: 检测橙色元素
            const hasOrangeElements = Array.from(document.querySelectorAll('*')).some(el => {
                const style = window.getComputedStyle(el);
                const bgColor = style.backgroundColor;
                const isOrange = bgColor.includes('rgb(255, 102') || bgColor.includes('rgb(255,102');
                if (isOrange) {
                    const rect = el.getBoundingClientRect();
                    if (rect.width * rect.height < 8000) return false;
                    if (style.visibility === 'hidden' || style.display === 'none' || style.opacity === '0') return false;
                    const elText = el.innerText || '';
                    return elText.includes('市场分析') || elText.includes('卖家精灵');
                }
                return false;
            });

            // 方法3: 检测特有类名
            const hasSpiritElements = Array.from(document.querySelectorAll('[class*="seller-spirit"], [class*="ss-"]'))
                .some(el => {
                    const rect = el.getBoundingClientRect();
                    const style = window.getComputedStyle(el);
                    if (rect.width * rect.height < 8000) return false;
                    return style.visibility !== 'hidden' && style.display !== 'none' && style.opacity !== '0';
                });

            return hasCharacteristicText || hasOrangeElements || hasSpiritElements;
        });

        // 如果卖家精灵面板还没有打开
        if (!hasSellerSpirit) {
            console.log('[0/3] 正在查找并点击卖家精灵按钮...');

            // 在页面的上下文中执行代码来查找并点击卖家精灵按钮
            const result = await page.evaluate(() => {
                // 用于记录使用的方法
                let methodUsed = '';

                // ----- 方法1: 通过文字内容查找（同时满足三个条件）-----
                // 获取页面中所有可能的元素
                const allElements = Array.from(document.querySelectorAll('span, div, button, a, img, i'));
                // 筛选出同时满足：包含"卖家精灵"文字 + 橙色背景 + 右侧位置
                const textCandidates = allElements
                    .map(el => {
                        // 获取元素的各种文本属性
                        const text = el.innerText || el.textContent || el.alt || el.title || '';
                        const rect = el.getBoundingClientRect();
                        const style = window.getComputedStyle(el);
                        const bgColor = style.backgroundColor;
                        return { el, text, rect, style, bgColor };
                    })
                    .filter(x => {
                        // 条件1: 必须包含特定文字
                        const hasText = x.text.includes('卖家精灵') || x.text.includes('Seller Spirit');
                        if (!hasText) return false;

                        // 条件2: 必须在右侧区域（右边缘大于75%屏幕宽度）
                        const isRightSide = x.rect.right > window.innerWidth * 0.75;
                        if (!isRightSide) return false;

                        // 条件3: 必须是橙色背景（rgb(255, 102, 0) 或类似橙色）
                        const isOrange = x.bgColor.includes('rgb(255, 102') ||
                                       x.bgColor.includes('rgb(255,102') ||
                                       x.bgColor.includes('orange');
                        if (!isOrange) return false;

                        // 必须可见
                        if (x.style.visibility === 'hidden' || x.style.display === 'none' || x.style.opacity === '0') {
                            return false;
                        }

                        // 严格限制尺寸：按钮通常比较小
                        // 宽度不超过 150 像素，高度不超过 150 像素
                        const isReasonableSize = x.rect.width <= 150 && x.rect.height <= 150;

                        // 面积小于 15000 平方像素（例如 100x100 的按钮）
                        const isSmallElement = (x.rect.width * x.rect.height) < 15000;

                        return isReasonableSize && isSmallElement;
                    });

                let sellerBtn = null;
                // 如果找到了同时满足三个条件的元素
                if (textCandidates.length > 0) {
                    // 记录使用的方法
                    methodUsed = '方法1: 文字内容+橙色背景+右侧位置（三条件同时满足）';
                    // 选择位置最靠右侧的元素（卖家精灵按钮通常在右侧）
                    let best = null;
                    for (const c of textCandidates) {
                        // 计算位置分数：主要看右侧位置 (rect.right)
                        const score = c.rect.right;
                        if (!best || score > best.score) {
                            best = { el: c.el, rect: c.rect, score, text: c.text, bgColor: c.bgColor };
                        }
                    }
                    sellerBtn = best && best.el;
                }

                // ----- 方法2: 通过固定定位查找（同时满足三个条件）-----
                // 如果方法1没找到，就查找右侧边缘的固定定位元素
                if (!sellerBtn) {
                    // 获取所有position:fixed的元素
                    const fixedElements = Array.from(document.querySelectorAll('[style*="position: fixed"], [style*="position:fixed"]'));
                    // 为每个元素计算位置分数
                    const candidates = fixedElements.map(el => {
                        const rect = el.getBoundingClientRect();
                        const style = window.getComputedStyle(el);
                        const bgColor = style.backgroundColor;
                        const text = el.innerText || el.textContent || el.alt || el.title || '';
                        const score = rect.right;
                        return { el, rect, text, score, style, bgColor };
                    }).filter(c => {
                        // 条件1: 右边缘大于75%屏幕宽度
                        const isRightSide = c.rect.right > window.innerWidth * 0.75;
                        if (!isRightSide) return false;

                        // 条件2: 包含"卖家精灵"文字
                        const hasText = c.text.includes('卖家精灵') || c.text.includes('Seller Spirit');
                        if (!hasText) return false;

                        // 条件3: 橙色背景
                        const isOrange = c.bgColor.includes('rgb(255, 102') ||
                                       c.bgColor.includes('rgb(255,102') ||
                                       c.bgColor.includes('orange');
                        if (!isOrange) return false;

                        // 必须可见
                        if (c.style.visibility === 'hidden' || c.style.display === 'none' || c.style.opacity === '0') {
                            return false;
                        }

                        // 严格限制尺寸
                        const isReasonableSize = c.rect.width <= 150 && c.rect.height <= 150;
                        const isSmallElement = (c.rect.width * c.rect.height) < 15000;

                        return isReasonableSize && isSmallElement;
                    });
                    // 如果找到了符合条件元素，选择最靠右侧的
                    if (candidates.length > 0) {
                        // 记录使用的方法
                        methodUsed = '方法2: 固定定位+文字+橙色+右侧（三条件同时满足）';
                        // 按分数降序排序
                        candidates.sort((a, b) => b.score - a.score);
                        sellerBtn = candidates[0].el;
                    }
                }

                // ----- 方法3: 通过橙色背景查找（同时满足三个条件）-----
                // 如果方法2也没找到，就查找橙色背景的元素（卖家精灵标志色是橙色）
                if (!sellerBtn) {
                    // 获取页面中所有元素
                    const allBottomRight = Array.from(document.querySelectorAll('*'));
                    const candidates = allBottomRight.map(el => {
                        const rect = el.getBoundingClientRect();
                        // 获取元素的计算样式
                        const style = window.getComputedStyle(el);
                        const bgColor = style.backgroundColor;
                        const text = el.innerText || el.textContent || el.alt || el.title || '';
                        // 判断是否为橙色（rgb(255, 102, 0) 或类似橙色）
                        const isOrange = bgColor.includes('rgb(255, 102') ||
                                       bgColor.includes('rgb(255,102') ||
                                       bgColor.includes('orange');
                        // 判断是否在右侧区域（右边缘大于75%屏幕宽度）
                        const isRightSide = rect.right > window.innerWidth * 0.75;
                        const score = rect.right;
                        return { el, rect, text, isOrange, isRightSide, score, style, bgColor };
                    }).filter(c => {
                        // 条件1: 必须在右侧
                        if (!c.isRightSide) return false;

                        // 条件2: 必须是橙色背景
                        if (!c.isOrange) return false;

                        // 条件3: 必须包含"卖家精灵"文字
                        const hasText = c.text.includes('卖家精灵') || c.text.includes('Seller Spirit');
                        if (!hasText) return false;

                        // 必须可见
                        if (c.style.visibility === 'hidden' || c.style.display === 'none' || c.style.opacity === '0') {
                            return false;
                        }

                        // 严格限制尺寸
                        const isReasonableSize = c.rect.width <= 150 && c.rect.height <= 150;
                        const isSmallElement = (c.rect.width * c.rect.height) < 15000;

                        return isReasonableSize && isSmallElement;
                    });

                    if (candidates.length > 0) {
                        // 记录使用的方法
                        methodUsed = '方法3: 橙色背景+文字+右侧（三条件同时满足）';
                        candidates.sort((a, b) => b.score - a.score);
                        sellerBtn = candidates[0].el;
                    }
                }

                // 如果找到了按钮
                if (sellerBtn) {
                    // 滚动到按钮位置，使其可见
                    // sellerBtn.scrollIntoView({ behavior: 'smooth', block: 'center' });

                    // 给按钮添加明显的红色边框和阴影，循环显示多次，每次30秒
                    let displayCount = 0;
                    const maxDisplays = 5; // 显示5次
                    const displayDuration = 30000; // 每次30秒

                    const showRedBox = () => {
                        if (displayCount < maxDisplays) {
                            displayCount++;
                            sellerBtn.style.outline = '3px solid red';
                            sellerBtn.style.boxShadow = '0 0 10px 3px red';

                            console.log(`[红框] 第 ${displayCount}/${maxDisplays} 次显示 (30秒)`);

                            setTimeout(() => {
                                sellerBtn.style.outline = '';
                                sellerBtn.style.boxShadow = '';

                                // 等待1秒后再次显示
                                if (displayCount < maxDisplays) {
                                    setTimeout(showRedBox, 1000);
                                }
                            }, displayDuration);
                        }
                    };

                    showRedBox(); // 开始第一次显示

                    // 获取按钮的位置信息
                    const rect = sellerBtn.getBoundingClientRect();
                    const text = sellerBtn.innerText || sellerBtn.textContent || sellerBtn.alt || sellerBtn.title || '';

                    // 记录详细的位置信息用于调试
                    console.log(`[调试] 按钮位置详情: top=${rect.top}, left=${rect.left}, width=${rect.width}, height=${rect.height}`);
                    console.log(`[调试] 按钮标签: ${sellerBtn.tagName}, 类名: ${sellerBtn.className}`);

                    // 计算中心坐标（确保使用整数）
                    const centerX = Math.round(rect.left + rect.width / 2);
                    const centerY = Math.round(rect.top + rect.height / 2);

                    // 验证坐标合理性
                    if (rect.width > 500 || rect.height > 200) {
                        console.log(`[!] 警告: 检测到的元素尺寸异常 (width=${rect.width}, height=${rect.height})`);
                        console.log(`[!] 可能检测到了容器元素而非实际按钮`);
                    }

                    // 返回找到按钮的结果（不点击，只标记）
                    return {
                        clicked: false,  // 改为false，表示只是找到了，还没点击
                        found: true,     // 新增：表示找到了按钮
                        method: methodUsed,  // 返回使用的方法
                        text,
                        x: centerX,  // 计算按钮中心X坐标
                        y: centerY,  // 计算按钮中心Y坐标
                        rectTop: Math.round(rect.top),
                        rectLeft: Math.round(rect.left),
                        rectWidth: Math.round(rect.width),
                        rectHeight: Math.round(rect.height)
                    };
                }
                // 没找到按钮，返回失败
                return { clicked: false, found: false, method: '未找到' };
            });

            // 如果在页面中成功找到了按钮
            if (result.found) {
                console.log(`[√] 找到卖家精灵按钮 (${result.method})`);
                console.log(`    按钮文字: ${result.text || '无文字'}`);
                console.log(`    按钮中心坐标: x=${Math.round(result.x)}, y=${Math.round(result.y)}`);
                if (result.rectTop !== undefined && result.rectLeft !== undefined) {
                    console.log(`    按钮位置: top=${result.rectTop}, left=${result.rectLeft}`);
                }
                if (result.rectWidth !== undefined && result.rectHeight !== undefined) {
                    console.log(`    按钮尺寸: width=${result.rectWidth}, height=${result.rectHeight}`);
                }
                console.log(`[i] 已用红框标记按钮，红框将一直显示`);

                // 如果有坐标信息，开始悬停和点击流程
                if (typeof result.x === 'number' && typeof result.y === 'number') {
                    const cx = Math.round(result.x);
                    const cy = Math.round(result.y);

                    // 增强版点击：使用多种方式确保触发
                    console.log('[*] 使用增强版点击策略...');

                    // 策略1: 鼠标移动 + 悬停 + 智能检测菜单展开
                    console.log('[*] 步骤1: 移动鼠标到按钮位置并悬停...');
                    await page.mouse.move(cx, cy);

                    // 触发悬停事件（不添加额外红框，因为按钮已经有红框了）
                    await page.evaluate((x, y) => {
                        const element = document.elementFromPoint(x, y);
                        if (element) {
                            // 触发悬停事件
                            ['mouseenter', 'mouseover'].forEach(eventType => {
                                const event = new MouseEvent(eventType, {
                                    view: window,
                                    bubbles: true,
                                    cancelable: true,
                                    clientX: x,
                                    clientY: y
                                });
                                element.dispatchEvent(event);
                            });
                        }
                    }, cx, cy);

                    console.log('[*] 悬停在按钮上，等待菜单展开...');

                    // 智能检测：等待菜单项出现（最多等待10秒）
                    let menuExpanded = false;
                    let waitTime = 0;
                    const maxWaitTime = 10;

                    while (waitTime < maxWaitTime && !menuExpanded) {
                        await new Promise(r => setTimeout(r, 1000));
                        waitTime++;

                        // 检测菜单是否已展开（查找"产品查询"等菜单项）
                        menuExpanded = await page.evaluate(() => {
                            const allElements = Array.from(document.querySelectorAll('span, div, button, a, li, [role="menuitem"]'));
                            const hasMenu = allElements.some(el => {
                                const text = (el.innerText || el.textContent || '').trim();
                                return (text === '产品查询' ||
                                        text === '关键词反查' ||
                                        text === '关键词挖掘' ||
                                        text.includes('产品查询')) &&
                                       el.offsetParent !== null;
                            });
                            return hasMenu;
                        });

                        if (menuExpanded) {
                            console.log(`[√] 菜单已展开 (等待${waitTime}秒)`);
                            break;
                        } else {
                            process.stdout.write(`\r[*] 等待菜单展开 (${waitTime}/${maxWaitTime}秒)...   `);
                        }
                    }

                    // 清除进度显示
                    process.stdout.write('\r' + ' '.repeat(50) + '\r');

                    if (!menuExpanded) {
                        console.log(`[!] 等待${maxWaitTime}秒后菜单未展开，继续执行点击`);
                    }

                    // 额外等待1秒确保菜单完全稳定
                    await new Promise(r => setTimeout(r, 1000));

                    // 策略2: 多次点击，每次间隔5秒（不添加额外红框，因为按钮已有红框）
                    for (let i = 0; i < 3; i++) {
                        console.log(`[*] 步骤2.${i + 1}: 执行第 ${i + 1} 次点击...`);
                        await page.mouse.click(cx, cy, { button: 'left', clickCount: 1 });
                        console.log(`[√] 已完成第 ${i + 1} 次点击 (x=${cx}, y=${cy})`);

                        if (i < 2) { // 最后一次点击后不需要等待
                            await countDown(5, `[*] 等待 ${i + 1} 次点击生效`);
                        }
                    }

                    // 策略3: 在页面内再次触发点击和各种事件
                    console.log('[*] 步骤3: 触发页面内事件...');
                    await page.evaluate((x, y) => {
                        const element = document.elementFromPoint(x, y);
                        if (element) {
                            console.log('[调试] 找到元素:', element.tagName, element.className);

                            // 触发多种事件
                            ['mousedown', 'mouseup', 'click', 'pointerdown', 'pointerup'].forEach(eventType => {
                                const event = new MouseEvent(eventType, {
                                    view: window,
                                    bubbles: true,
                                    cancelable: true,
                                    clientX: x,
                                    clientY: y
                                });
                                element.dispatchEvent(event);
                            });

                            // 如果元素有click方法，直接调用
                            if (typeof element.click === 'function') {
                                element.click();
                            }
                        }
                    }, cx, cy);
                    console.log('[√] 页面内事件已触发');
                }

                // 等待10秒让面板加载
                console.log('[*] 等待卖家精灵面板加载 (10秒)...');
                await countDown(10, '[*] 等待面板加载');

                // ===== 增强版：点击"产品查询"菜单项 =====
                console.log('[*] 正在查找并点击"产品查询"菜单项...');

                // 先等待5秒，确保面板完全展开
                console.log('[*] 等待面板完全展开 (5秒)...');
                await countDown(5, '[*] 等待面板展开');

                const menuClickResult = await page.evaluate(() => {
                    // 查找包含"产品查询"文字的元素
                    const allElements = Array.from(document.querySelectorAll('span, div, button, a, li, [role="menuitem"]'));

                    console.log('[调试] 搜索"产品查询"菜单项，共找到', allElements.length, '个候选元素');

                    // 打印所有可能的菜单项（用于调试）
                    const possibleMenus = allElements.filter(el => {
                        const text = (el.innerText || el.textContent || '').trim();
                        return text.length > 0 && text.length < 20; // 菜单项通常文字较短
                    }).slice(0, 20); // 只打印前20个

                    console.log('[调试] 可能的菜单项:', possibleMenus.map(el => el.innerText || el.textContent).join(', '));

                    const menuItem = allElements.find(el => {
                        const text = (el.innerText || el.textContent || '').trim();
                        return text === '产品查询' || text.includes('产品查询') || text === 'Product Query';
                    });

                    if (menuItem && menuItem.offsetParent !== null) {
                        console.log('[调试] 找到"产品查询"菜单项:', menuItem.tagName, menuItem.className);

                        // 给元素添加红色高亮
                        const prevOutline = menuItem.style.outline;
                        const prevBoxShadow = menuItem.style.boxShadow;
                        menuItem.style.outline = '3px solid red';
                        menuItem.style.boxShadow = '0 0 10px 3px red';

                        // 滚动到元素位置
                        // menuItem.scrollIntoView({ behavior: 'smooth', block: 'center' });

                        // 获取位置信息
                        const rect = menuItem.getBoundingClientRect();

                        // 触发多种事件
                        ['mouseenter', 'mouseover', 'mousedown', 'mouseup', 'click'].forEach(eventType => {
                            const event = new MouseEvent(eventType, {
                                view: window,
                                bubbles: true,
                                cancelable: true,
                                clientX: rect.left + rect.width / 2,
                                clientY: rect.top + rect.height / 2
                            });
                            menuItem.dispatchEvent(event);
                        });

                        // 直接调用click方法
                        menuItem.click();

                        // 5秒后恢复样式
                        setTimeout(() => {
                            menuItem.style.outline = prevOutline;
                            menuItem.style.boxShadow = prevBoxShadow;
                        }, 5000);

                        return {
                            clicked: true,
                            text: menuItem.innerText || menuItem.textContent,
                            x: rect.left + rect.width / 2,
                            y: rect.top + rect.height / 2
                        };
                    }

                    console.log('[调试] 未找到"产品查询"菜单项');
                    return { clicked: false };
                });

                if (menuClickResult.clicked) {
                    console.log(`[√] 已点击"产品查询"菜单项 (${menuClickResult.text})`);

                    // 如果有坐标，使用鼠标多次点击确保触发
                    if (typeof menuClickResult.x === 'number' && typeof menuClickResult.y === 'number') {
                        const mx = Math.round(menuClickResult.x);
                        const my = Math.round(menuClickResult.y);
                        console.log(`[*] 使用鼠标增强点击菜单项 (x=${mx}, y=${my})`);

                        // 鼠标移动到位置
                        console.log('[*] 移动鼠标到菜单项...');
                        await page.mouse.move(mx, my);
                        await new Promise(r => setTimeout(r, 1000));

                        // 多次点击，每次间隔5秒
                        for (let i = 0; i < 3; i++) {
                            console.log(`[*] 菜单点击第 ${i + 1} 次...`);
                            await page.mouse.click(mx, my, { button: 'left', clickCount: 1 });
                            console.log(`[√] 已完成菜单第 ${i + 1} 次点击`);

                            if (i < 2) { // 最后一次点击后不需要等待
                                await countDown(5, `[*] 等待菜单第 ${i + 1} 次点击生效`);
                            }
                        }
                    }

                    // 等待10秒让数据面板加载
                    console.log('[*] 等待数据面板加载 (10秒)...');
                    await countDown(10, '[*] 等待数据面板加载');
                } else {
                    console.log('[!] 未找到"产品查询"菜单项');
                    console.log('[*] 尝试查找其他可能的菜单项...');

                    // 尝试查找并点击任何看起来像菜单的元素
                    const alternativeClick = await page.evaluate(() => {
                        // 查找所有可能是菜单的元素
                        const candidates = Array.from(document.querySelectorAll('li, [role="menuitem"], .menu-item, [class*="menu"]'));

                        if (candidates.length > 0) {
                            console.log('[调试] 找到', candidates.length, '个可能的菜单元素');
                            console.log('[调试] 菜单文字:', candidates.slice(0, 10).map(el => el.innerText || el.textContent).join(', '));

                            // 尝试点击第一个可见的菜单项
                            const firstVisible = candidates.find(el => el.offsetParent !== null);
                            if (firstVisible) {
                                firstVisible.click();
                                return { clicked: true, text: firstVisible.innerText || firstVisible.textContent };
                            }
                        }
                        return { clicked: false };
                    });

                    if (alternativeClick.clicked) {
                        console.log(`[√] 已点击替代菜单项 (${alternativeClick.text})`);
                        console.log('[*] 等待替代菜单响应 (5秒)...');
                        await countDown(5, '[*] 等待替代菜单响应');
                    }
                }

            } else {
                console.log('[!] 未找到卖家精灵按钮，尝试直接等待数据...');
            }
        } else {
            // 如果卖家精灵面板已经存在
            console.log('[√] 卖家精灵面板已存在');
        }

        console.log('[*] 正在等待卖家精灵数据出现...');

        // ===== 调试：截图保存当前页面状态 =====
        try {
            const screenshotPath = path.resolve(process.cwd(), 'debug_screenshot.png');
            await page.screenshot({ path: screenshotPath, fullPage: false });
            console.log(`[i] 已保存页面截图到: ${screenshotPath}`);
        } catch (e) {
            console.log(`[!] 截图失败: ${e.message}`);
        }

        // ===== 调试：输出页面中的关键信息 =====
        const debugInfo = await page.evaluate(() => {
            const bodyText = document.body.innerText;

            // 检查是否有卖家精灵相关的元素
            const sellerSpiritElements = Array.from(document.querySelectorAll('[class*="seller"], [class*="spirit"], [id*="seller"]'));

            // 检查是否有数据相关的文字
            const hasDataText = bodyText.includes('加载数据') || bodyText.includes('总销量') || bodyText.includes('导出明细');

            // 检查是否有登录相关的文字
            const hasLoginText = bodyText.includes('登录') || bodyText.includes('Sign in');

            // 获取所有可见的按钮文字
            const buttons = Array.from(document.querySelectorAll('button, [role="button"]'))
                .filter(btn => btn.offsetParent !== null)
                .map(btn => btn.innerText || btn.textContent)
                .filter(text => text && text.trim().length > 0)
                .slice(0, 20);

            return {
                hasSellerSpiritElements: sellerSpiritElements.length,
                hasDataText,
                hasLoginText,
                visibleButtons: buttons,
                bodyTextSample: bodyText.substring(0, 500) // 前500个字符
            };
        });

        console.log('[调试] 页面状态信息:');
        console.log(`  - 卖家精灵元素数量: ${debugInfo.hasSellerSpiritElements}`);
        console.log(`  - 是否有数据文字: ${debugInfo.hasDataText}`);
        console.log(`  - 是否有登录文字: ${debugInfo.hasLoginText}`);
        console.log(`  - 可见按钮 (前20个): ${debugInfo.visibleButtons.join(', ')}`);
        console.log(`  - 页面文字样本: ${debugInfo.bodyTextSample.substring(0, 200)}...`);

        // ===== 步骤3: 检查是否需要登录 =====
        // 在页面中执行代码检查是否有登录界面
        const needLogin = await page.evaluate(() => {
            // 检查页面是否包含登录相关的文字或输入框
            const hasSignIn = document.body.innerText.includes('登录') ||
                            document.body.innerText.includes('Sign in') ||
                            document.body.innerText.includes('账号登录') ||
                            document.querySelector('input[type="email"]') ||
                            document.querySelector('input[name="email"]');

            return hasSignIn;
        });

        // 如果检测到登录界面
        if (needLogin) {
            console.log('[!] 检测到登录界面，正在查找卖家精灵登录按钮...');

            // 在页面中查找并点击卖家精灵的登录按钮
            const loginClicked = await page.evaluate(() => {
                // 尝试通过类名找到卖家精灵面板容器
                const spiritPanel = document.querySelector('.ss-spirit-panel') ||
                                   document.querySelector('[class*="seller-spirit"]') ||
                                   document.querySelector('[class*="ss-panel"]') ||
                                   document.querySelector('[id*="seller"]');

                // 在面板内查找登录按钮
                let loginBtn = null;
                if (spiritPanel) {
                    // 在面板内查找所有可能的按钮元素
                    const buttons = spiritPanel.querySelectorAll('button, div[role="button"], span, a');
                    loginBtn = Array.from(buttons).find(btn => {
                        const text = btn.innerText && btn.innerText.trim();
                        // 检查按钮文字是否为登录相关
                        return text === '登录' ||
                               text === '账号登录' ||
                               text === '立即登录' ||
                               text === 'Login';
                    });
                }

                // 如果面板内没找到，通过位置判断（右下角的登录按钮通常是卖家精灵的）
                if (!loginBtn) {
                    // 获取页面中所有可能的按钮
                    const allButtons = Array.from(document.querySelectorAll('button, div[role="button"], span, a'));
                    const candidates = allButtons.filter(btn => {
                        const text = btn.innerText && btn.innerText.trim();
                        // 判断是否是登录按钮
                        const isLoginBtn = text === '登录' || text === '立即登录' || text === 'Login';
                        if (!isLoginBtn || !btn.offsetParent) return false;

                        // 获取按钮位置
                        const rect = btn.getBoundingClientRect();
                        // 判断是否在页面右侧边缘（卖家精灵面板通常在右侧边缘）
                        const isBottomRight = rect.bottom > window.innerHeight * 0.5 &&
                                             rect.right > window.innerWidth * 0.85;
                        return isBottomRight;
                    });

                    if (candidates.length > 0) {
                        // 选择最靠右下角的按钮
                        candidates.sort((a, b) => {
                            const rectA = a.getBoundingClientRect();
                            const rectB = b.getBoundingClientRect();
                            // 比较bottom+right的值，越大的越靠右下角
                            return (rectB.bottom + rectB.right) - (rectA.bottom + rectA.right);
                        });
                        loginBtn = candidates[0];
                    }
                }

                // 如果找到了登录按钮
                if (loginBtn) {
                    // 给按钮添加红色高亮
                    const prevOutline = loginBtn.style.outline;
                    const prevBoxShadow = loginBtn.style.boxShadow;
                    loginBtn.style.outline = '3px solid red';
                    loginBtn.style.boxShadow = '0 0 10px 3px red';

                    // 滚动到按钮可见位置
                    // loginBtn.scrollIntoView({ behavior: 'smooth', block: 'center' });

                    // 点击登录按钮
                    loginBtn.click();

                    // 5秒后恢复样式
                    setTimeout(() => {
                        loginBtn.style.outline = prevOutline;
                        loginBtn.style.boxShadow = prevBoxShadow;
                    }, 5000);

                    return { success: true, text: loginBtn.innerText };
                }

                // 没找到登录按钮
                return { success: false, text: null };
            });

            // 如果成功点击了登录按钮
            if (loginClicked.success) {
                console.log(`[√] 已点击登录按钮 (${loginClicked.text})`);
                // 等待3秒让页面响应
                await new Promise(r => setTimeout(r, 3000));

                // 等待数据加载，最多等待30秒
                console.log('[*] 等待数据加载...');
                let dataLoaded = false;
                // 循环30次，每次等待1秒
                for (let i = 0; i < 30; i++) {
                    await new Promise(r => setTimeout(r, 1000));

                    // 检查数据是否已加载
                    const hasData = await page.evaluate(() => {
                        // 使用正则表达式匹配"当前页 X个商品"的文字
                        const match = document.body.innerText.match(/当前页\s*(\d+)\s*个商品/);
                        return {
                            hasData: !!match,
                            count: match ? parseInt(match[1]) : 0
                        };
                    });

                    // 如果检测到数据且数据量大于0
                    if (hasData.hasData && hasData.count > 0) {
                        console.log(`[√] 数据已加载 (${hasData.count} 条)`);
                        dataLoaded = true;
                        break; // 跳出循环
                    }

                    // 显示等待进度
                    process.stdout.write(`\r[*] 等待数据加载 (${i + 1}/30秒)...   `);
                }

                // 如果数据加载超时
                if (!dataLoaded) {
                    console.log('\n[!] 数据加载超时，但继续执行...');
                } else {
                    // 清除等待提示
                    process.stdout.write('\r' + ' '.repeat(50) + '\r');
                }
            } else {
                console.log('[!] 未找到卖家精灵登录按钮');
            }
        }

        // ===== 步骤4: 点击卖家精灵按键，让卖家精灵数据面板出现 =====
        // 通过点击卖家精灵按键，让卖家精灵数据面板出现
        console.log('[*] 点击卖家精灵按键，让卖家精灵数据面板出现...');
        let detectionResult = { found: false, method: '未找到' };
        try {
            const handle = await page.waitForFunction(() => {
                const bodyText = document.body.innerText;
                let foundEl = null;
                let methodUsed = '';

                // 方法1（优先级最高）: 检测卖家精灵特有的类名或ID（最可靠）
                const spiritEl = Array.from(document.querySelectorAll('[class*="seller-spirit"], [class*="ss-"], [id*="seller-spirit"], [id*="sellerspirit"]'))
                    .find(el => {
                        const rect = el.getBoundingClientRect();
                        const style = window.getComputedStyle(el);

                        // A. 基础可见性检查 - 忽略完全透明或隐藏的元素
                        if (style.display === 'none' ||
                            style.visibility === 'hidden' ||
                            style.opacity === '0' ||
                            rect.width === 0) {
                            return false;
                        }

                        // B. 关键位置检查 - 找右侧悬浮按钮
                        // 1. 必须在屏幕右侧区域（元素右边缘距离屏幕右边缘小于150px）
                        const isOnRightSide = (window.innerWidth - rect.right) < 150;
                        // 2. 必须在垂直可视范围内
                        const isInViewport = rect.top >= 0 && rect.top <= window.innerHeight;

                        if (!isOnRightSide || !isInViewport) return false;

                        // C. 尺寸检查 - 区分"按钮"和"大面板"
                        // 大面板宽度通常很大(>500px)，按钮通常较小
                        // 限制宽度小于150px，且高度大于20px（防止选中微小装饰点）
                        const isButtonSize = rect.width < 150 && rect.width > 20 && rect.height > 20;

                        if (!isButtonSize) return false;

                        // D. 悬浮特征检查 - 右侧按钮通常是fixed定位且z-index很高
                        const isFloating = style.position === 'fixed' || parseInt(style.zIndex) > 100;

                        return isFloating;
                    });

                if (spiritEl) {
                    foundEl = spiritEl;
                    methodUsed = '方法1: 特有类名/ID（优先）';
                }

                // 方法2: 检测卖家精灵文字 + 橙色元素
                if (!foundEl) {
                    const dataStrings = ['卖家精灵'];
                    const candidates = Array.from(document.querySelectorAll('span, div, button, *')).filter(el => {
                        const text = el.innerText || el.textContent || '';
                        const rect = el.getBoundingClientRect();
                        const style = window.getComputedStyle(el);

                        // 检查文字特征
                        const hasText = dataStrings.some(s => text.includes(s)) || text.match(/当前页\s*\d+\s*个商品/);

                        // 检查橙色特征
                        const bgColor = style.backgroundColor;
                        const color = style.color;
                        const isOrange =
                            bgColor.includes('rgb(255, 102') ||
                            bgColor.includes('rgb(255,102') ||
                            bgColor.includes('rgb(255, 103') ||
                            bgColor.includes('rgb(255,103') ||
                            color.includes('rgb(255, 102') ||
                            color.includes('rgb(255,102');

                        // 必须满足文字或颜色特征之一
                        if (!hasText && !isOrange) return false;

                        // 可见性检查
                        const isVisible = el.offsetParent !== null &&
                                         style.visibility !== 'hidden' &&
                                         style.display !== 'none' &&
                                         style.opacity !== '0';
                        if (!isVisible) return false;

                        // 严格的尺寸检查：必须有实际的宽度和高度
                        if (rect.width < 50 || rect.height < 20) return false;

                        // 排除过大的容器元素
                        if (rect.width > 1500 || rect.height > 1000) return false;

                        // 位置检查：必须在视口内或视口下方合理范围
                        const isInViewport = rect.top >= 0 && rect.top < window.innerHeight * 2;
                        const hasReasonablePosition = rect.top < 5000;

                        return isInViewport && hasReasonablePosition;
                    });

                    // 如果找到多个候选元素，优先选择：
                    // 1. 有"卖家精灵"文字的
                    // 2. 尺寸适中的（不要太大的容器）
                    // 3. 位置靠右的
                    if (candidates.length > 0) {
                        candidates.sort((a, b) => {
                            const aText = (a.innerText || '').includes('卖家精灵');
                            const bText = (b.innerText || '').includes('卖家精灵');
                            if (aText && !bText) return -1;
                            if (!aText && bText) return 1;

                            const aRect = a.getBoundingClientRect();
                            const bRect = b.getBoundingClientRect();

                            // 优先选择尺寸适中的（面积在50-500k像素之间）
                            const aArea = aRect.width * aRect.height;
                            const bArea = bRect.width * bRect.height;
                            const aGoodSize = aArea > 5000 && aArea < 500000;
                            const bGoodSize = bArea > 5000 && bArea < 500000;
                            if (aGoodSize && !bGoodSize) return -1;
                            if (!aGoodSize && bGoodSize) return 1;

                            // 其次选择位置靠右的
                            return bRect.right - aRect.right;
                        });

                        foundEl = candidates[0];
                        methodUsed = '方法2: 文字+橙色检测（增强）+智能排序';
                    }
                }

                if (foundEl) {
                    foundEl.style.outline = '3px solid red';
                    foundEl.style.boxShadow = '0 0 10px 3px red';
                    const rect = foundEl.getBoundingClientRect();

                    // 记录详细的位置信息用于调试
                    console.log(`[调试] 检测到元素位置: top=${rect.top}, left=${rect.left}, width=${rect.width}, height=${rect.height}`);
                    console.log(`[调试] 元素标签: ${foundEl.tagName}, 类名: ${foundEl.className}`);

                    // 计算中心坐标
                    const centerX = Math.round(rect.left + rect.width / 2);
                    const centerY = Math.round(rect.top + rect.height / 2);

                    // 验证坐标合理性
                    if (rect.width > 800 || rect.height > 600) {
                        console.log(`[!] 警告: 检测到的元素尺寸异常 (width=${rect.width}, height=${rect.height})`);
                        console.log(`[!] 可能检测到了容器元素而非实际面板`);
                    }

                    return {
                        found: true,
                        method: methodUsed,
                        text: foundEl.innerText.substring(0, 50).trim(),
                        x: centerX,
                        y: centerY,
                        rectTop: Math.round(rect.top),
                        rectLeft: Math.round(rect.left),
                        rectWidth: Math.round(rect.width),
                        rectHeight: Math.round(rect.height)
                    };
                }

                return false;
            }, { timeout: USER_WAIT_TIMEOUT });

            detectionResult = await handle.jsonValue();
            
            if (detectionResult.x && detectionResult.y) {
                console.log(`    中心坐标: x=${detectionResult.x}, y=${detectionResult.y}`);
            }
            if (detectionResult.rectTop !== undefined && detectionResult.rectLeft !== undefined) {
                console.log(`    元素位置: top=${detectionResult.rectTop}, left=${detectionResult.rectLeft}`);
                console.log(`[√] 找到卖家精灵按键/面板 (${detectionResult.method})`);
            if (detectionResult.text) console.log(`    检测到内容: ${detectionResult.text}`);
            }
            if (detectionResult.rectWidth !== undefined && detectionResult.rectHeight !== undefined) {
                console.log(`    元素尺寸: width=${detectionResult.rectWidth}, height=${detectionResult.rectHeight}`);
            }
            console.log(`[i] 已用红框标记检测到的元素`);

            // 验证坐标是否合理
            if (detectionResult.y > 5000) {
                console.log(`[!] 警告: Y坐标过大 (${detectionResult.y})，可能检测到错误元素`);
            } else if (detectionResult.rectWidth > 800 || detectionResult.rectHeight > 600) {
                console.log(`[!] 警告: 元素尺寸异常，可能检测到容器而非按钮`);
            } else {
                console.log(`[√] 坐标位置验证通过`);
                console.log(`[√] 坐标位置验证通过，，，坐标的位置找对了，，多点击几次`);
            }

            // 如果找到了按钮，执行多次点击
            if (detectionResult.found && detectionResult.x && detectionResult.y) {
                const clickX = detectionResult.x;
                const clickY = detectionResult.y;

                console.log(`[*] 开始执行多次点击操作...`);

                // 执行3次点击，每次间隔3秒
                for (let i = 0; i < 3; i++) {
                    console.log(`[*] 执行第 ${i + 1} 次点击 (x=${clickX}, y=${clickY})...`);
                    await page.mouse.click(clickX, clickY, { button: 'left', clickCount: 1 });
                    console.log(`[√] 已完成第 ${i + 1} 次点击`);

                    if (i < 2) { // 最后一次点击后不需要等待
                        await countDown(3, `[*] 等待第 ${i + 1} 次点击生效`);
                    }
                }

                console.log(`[√] 多次点击完成，等待面板响应...`);
                await new Promise(r => setTimeout(r, 2000)); // 额外等待2秒
            }
        } catch (err) {
            console.log('[!] 未找到卖家精灵按键/面板');
        }

        // console.log('[√] 卖家精灵面板已出现');

        // ===== 步骤5: 等待数据加载完成（使用多种检测方式） =====
        console.log('[*] 等待数据加载完成（使用多种检测方式）...');
        console.log('[*] 提示：卖家精灵数据加载可能需要较长时间，请耐心等待...');

        let dataLoadWaitTime = 0;
        const maxDataLoadWait = 180; // 增加到180秒（3分钟）
        let dataLoaded = false;
        let lastCheckTime = Date.now();

        while (dataLoadWaitTime < maxDataLoadWait) {
            await new Promise(r => setTimeout(r, 1000));
            dataLoadWaitTime++;

            // 检查是否有数据加载（使用多种检测方式）
            const checkResult = await page.evaluate(() => {
                const bodyText = document.body.innerText;

                // 方法1: 匹配"当前页 X个商品"
                const match1 = bodyText.match(/当前页\s*(\d+)\s*个商品/);

                // 方法2: 匹配"已加载 X 条"
                const match2 = bodyText.match(/已加载\s*(\d+)\s*条/);

                // 方法3: 匹配"共 X 条"或"总计 X 条"
                const match3 = bodyText.match(/[共总计]\s*(\d+)\s*条/);

                // 方法4: 检查是否有"加载更多"按钮（说明数据已经开始加载）
                const elms = Array.from(document.querySelectorAll('button, div, span'));
                const hasLoadMoreBtn = elms.some(e =>
                    e.innerText && e.innerText.trim() === '加载更多' &&
                    e.offsetParent !== null
                );

                // 方法5: 检查是否有"导出明细"按钮（说明数据面板已完全加载）
                const hasExportBtn = elms.some(e => {
                    const text = (e.innerText || '').trim();
                    return (text === '导出明细' || text === '导出' || text.includes('导出')) &&
                           e.offsetParent !== null;
                });

                // 方法6: 检查是否有数据表格（table元素且行数>1）
                const tables = Array.from(document.querySelectorAll('table'));
                const hasDataTable = tables.some(table => {
                    const rows = table.querySelectorAll('tr');
                    return rows.length > 1 && table.offsetParent !== null;
                });

                // 方法7: 检查是否有ASIN列表（常见的产品标识）
                const hasAsinData = bodyText.match(/B0[A-Z0-9]{8,}/g);
                const asinCount = hasAsinData ? hasAsinData.length : 0;

                // 综合判断：任何一种方法检测到数据都算成功
                const match = match1 || match2 || match3;
                const count = match ? parseInt(match[1]) : 0;

                // 如果有数据计数，或者有"加载更多"按钮，或者有导出按钮+数据表格，都认为数据已加载
                const hasData = (count > 0) ||
                               (hasLoadMoreBtn) ||
                               (hasExportBtn && hasDataTable) ||
                               (asinCount >= 5); // 至少5个ASIN

                return {
                    hasData: hasData,
                    count: count,
                    hasLoadMoreBtn: hasLoadMoreBtn,
                    hasExportBtn: hasExportBtn,
                    hasDataTable: hasDataTable,
                    asinCount: asinCount,
                    detectionMethod: match1 ? '当前页X个商品' :
                                    match2 ? '已加载X条' :
                                    match3 ? '共X条' :
                                    hasLoadMoreBtn ? '加载更多按钮' :
                                    hasExportBtn && hasDataTable ? '导出按钮+数据表格' :
                                    asinCount >= 5 ? `ASIN数据(${asinCount}个)` : '未检测到'
                };
            });

            if (checkResult.hasData) {
                console.log(`\n[√] 数据已加载！检测方式: ${checkResult.detectionMethod}`);
                if (checkResult.count > 0) {
                    console.log(`[√] 当前数据量: ${checkResult.count} 条`);
                }
                if (checkResult.asinCount > 0) {
                    console.log(`[√] 检测到 ${checkResult.asinCount} 个ASIN产品`);
                }
                dataLoaded = true;
                break;
            }

            // 每5秒显示一次进度和检测状态
            if (dataLoadWaitTime % 5 === 0) {
                const status = [];
                if (checkResult.hasLoadMoreBtn) status.push('有加载更多按钮');
                if (checkResult.hasExportBtn) status.push('有导出按钮');
                if (checkResult.hasDataTable) status.push('有数据表格');
                if (checkResult.asinCount > 0) status.push(`${checkResult.asinCount}个ASIN`);

                const statusText = status.length > 0 ? ` [${status.join(', ')}]` : '';
                process.stdout.write(`\r[*] 等待数据加载 (${dataLoadWaitTime}/${maxDataLoadWait}秒)${statusText}...   `);
            } else {
                process.stdout.write(`\r[*] 等待数据加载 (${dataLoadWaitTime}/${maxDataLoadWait}秒)...   `);
            }

            // 每30秒尝试重新点击一次卖家精灵按钮（仅在数据面板未出现时）
            if (dataLoadWaitTime % 30 === 0 && dataLoadWaitTime > 0 && !dataLoaded) {
                // 先检查数据面板是否已经出现
                const panelExists = await page.evaluate(() => {
                    const bodyText = document.body.innerText;
                    // 检查是否有卖家精灵数据面板的特征
                    const hasPanel = bodyText.includes('总销量') ||
                                    bodyText.includes('总销售额') ||
                                    bodyText.includes('平均销量') ||
                                    bodyText.includes('导出明细') ||
                                    document.querySelector('[class*="seller-spirit"]') !== null ||
                                    document.querySelector('[class*="sellerSpirit"]') !== null;
                    return hasPanel;
                });

                // 只有在面板不存在时才重新点击
                if (!panelExists) {
                    console.log(`\n[*] 已等待${dataLoadWaitTime}秒，数据面板未出现，尝试重新点击卖家精灵按钮...`);

                    const reClickResult = await page.evaluate(() => {
                        // 查找卖家精灵按钮
                        const allElements = Array.from(document.querySelectorAll('span, div, button, a, img, i'));
                        const textCandidates = allElements
                            .map(el => {
                                const text = el.innerText || el.textContent || el.alt || el.title || '';
                                return { el, text };
                            })
                            .filter(x => x.text.includes('卖家精灵') || x.text.includes('Seller Spirit'));

                        if (textCandidates.length > 0) {
                            let best = null;
                            for (const c of textCandidates) {
                                const rect = c.el.getBoundingClientRect();
                                const score = rect.bottom + rect.right;
                                if (!best || score > best.score) {
                                    best = { el: c.el, rect, score };
                                }
                            }

                            if (best) {
                                best.el.click();
                                return { clicked: true };
                            }
                        }
                        return { clicked: false };
                    });

                    if (reClickResult.clicked) {
                        console.log('[√] 已重新点击卖家精灵按钮');
                        await new Promise(r => setTimeout(r, 3000)); // 等待3秒
                    }
                } else {
                    console.log(`\n[*] 已等待${dataLoadWaitTime}秒，数据面板已存在，跳过重新点击`);
                }
            }
        }

        // 清除进度显示
        process.stdout.write('\r' + ' '.repeat(60) + '\r');

        if (!dataLoaded) {
            console.log(`[!] 警告：等待${maxDataLoadWait}秒后仍未检测到数据`);
            console.log('[!] 可能原因：');
            console.log('    1. 卖家精灵扩展未正确加载');
            console.log('    2. 需要登录卖家精灵账号');
            console.log('    3. 网络连接问题导致数据加载缓慢');
            console.log('[*] 建议：手动检查浏览器中的卖家精灵面板状态');
            console.log('[*] 脚本将继续执行，但可能无法正确导出数据...');
        }

        // 再等待5秒确保数据完全加载
        console.log('[*] 等待5秒确保数据完全加载...');
        await new Promise(r => setTimeout(r, 5000));

        // 检查数据状态并显示检测方法
        const dataStatus = await page.evaluate(() => {
            const bodyText = document.body.innerText;
            const match = bodyText.match(/当前页\s*(\d+)\s*个商品/);

            // 检测使用的方法
            const detectionMethods = [];

            // 检测特征文字
            if (bodyText.includes('总销量') || bodyText.includes('总销售额') || bodyText.includes('平均销量')) {
                detectionMethods.push('特征文字(总销量/总销售额/平均销量)');
            }

            // 检测数据加载文字
            if (match) {
                detectionMethods.push(`数据加载文字(${match[0]})`);
            }

            // 检测导出按钮
            if (bodyText.includes('导出明细')) {
                detectionMethods.push('导出明细按钮');
            }

            // 检测橙色元素
            const hasOrangeElements = Array.from(document.querySelectorAll('*')).some(el => {
                const style = window.getComputedStyle(el);
                const bgColor = style.backgroundColor;
                const isOrange = bgColor.includes('rgb(255, 102') || bgColor.includes('rgb(255,102');
                if (isOrange) {
                    const text = el.innerText || '';
                    return text.includes('市场分析') || text.includes('卖家精灵');
                }
                return false;
            });
            if (hasOrangeElements) {
                detectionMethods.push('橙色元素(市场分析/卖家精灵)');
            }

            // 检测特有类名
            if (document.querySelector('[class*="seller-spirit"]') || document.querySelector('[class*="ss-"]')) {
                detectionMethods.push('特有类名(seller-spirit/ss-)');
            }

            return {
                count: match ? parseInt(match[1]) : 0,
                hasData: !!match,
                hasExportBtn: bodyText.includes('导出明细'),
                detectionMethods: detectionMethods
            };
        });

        // 如果检测到数据
        if (dataStatus.hasData) {
            console.log(`[√] 卖家精灵数据已出现！当前数据量: ${dataStatus.count} 条`);
            if (dataStatus.detectionMethods.length > 0) {
                console.log(`[i] 检测方法: ${dataStatus.detectionMethods.join(', ')}`);
            }
        } else {
            console.log('[!] 警告：未检测到数据计数，但继续执行...');
            if (dataStatus.detectionMethods.length > 0) {
                console.log(`[i] 已检测到卖家精灵面板: ${dataStatus.detectionMethods.join(', ')}`);
            }
        }

        // ========================================
        // 第一阶段：加载全部数据
        // ========================================
        console.log('\n' + '='.repeat(60));
        console.log('[2/3] 第一阶段：加载全部数据');
        console.log('='.repeat(60));
        // 记录上一次的数据量
        let lastCount = 0;
        // 记录数据量开始不变的时间
        let noChangeStartTime = null;
        // 30秒不变阈值（毫秒）
        const NO_CHANGE_THRESHOLD = 30000;

        // 无限循环，直到所有数据加载完成
        while (true) {
            // 在页面中执行代码，获取当前状态
            const status = await page.evaluate(() => {
                // 匹配"当前页 X个商品"获取当前数据量
                const match = document.body.innerText.match(/当前页\s*(\d+)\s*个商品/);
                const count = match ? parseInt(match[1]) : 0;

                // 查找"加载更多"按钮
                const elms = Array.from(document.querySelectorAll('button, div, span'));
                const loadBtn = elms.find(e =>
                    e.innerText && e.innerText.trim() === '加载更多' &&
                    e.offsetParent !== null && e.children.length === 0
                );

                let pos = null;
                // 如果找到了"加载更多"按钮
                if (loadBtn) {
                    // 滚动到按钮位置
                    loadBtn.scrollIntoView({ behavior: 'smooth', block: 'center' });
                    // 获取按钮位置坐标
                    const r = loadBtn.getBoundingClientRect();
                    pos = { x: r.left + r.width / 2, y: r.top + r.height / 2 };

                    // 给按钮添加红色高亮，持续60秒
                    const prevOutline = loadBtn.style.outline;
                    const prevBoxShadow = loadBtn.style.boxShadow;
                    loadBtn.style.outline = '3px solid red';
                    loadBtn.style.boxShadow = '0 0 10px 3px red';
                    // 60秒后恢复样式
                    setTimeout(() => {
                        loadBtn.style.outline = prevOutline;
                        loadBtn.style.boxShadow = prevBoxShadow;
                    }, 60000);
                }

                // 返回状态信息
                return {
                    count,
                    hasBtn: !!loadBtn,
                    pos,
                    finished: document.body.innerText.includes('没有更多了')
                };
            });

            // 显示当前数据量
            console.log(`  📊 当前数据量: ${status.count} 条`);

            // 检查数据量是否变化（只在有"加载更多"按钮时才等待）
            if (status.hasBtn) {
                // 有"加载更多"按钮，需要检查数据量变化
                if (status.count === lastCount) {
                    // 数据量没有变化
                    const now = Date.now();
                    if (noChangeStartTime === null) {
                        // 第一次检测到不变，记录开始时间
                        noChangeStartTime = now;
                        console.log('  ⏳ 数据量未变化，开始 30s 计时...');
                    } else {
                        // 计算已经等待的时间
                        const noChangeDuration = now - noChangeStartTime;
                        const waited = Math.floor(noChangeDuration / 1000);
                        const remainingSeconds = Math.max(0, Math.ceil((NO_CHANGE_THRESHOLD - noChangeDuration) / 1000));
                        // 显示等待进度
                        process.stdout.write(`\r  ⏳ 数据量未变化，已等待 ${waited}s，还需等待 ${remainingSeconds}s...    `);

                        // 如果30秒以上没变化，进入第二阶段
                        if (noChangeDuration >= NO_CHANGE_THRESHOLD) {
                            process.stdout.write('\r' + ' '.repeat(80) + '\r');
                            console.log(`  ✓ 数据加载完成 (${status.count} 条，连续 ${waited}s 未变化)`);
                            break; // 跳出循环
                        }
                    }
                } else {
                    // 数据量有变化，重置计时器
                    if (noChangeStartTime !== null) {
                        const duration = Date.now() - noChangeStartTime;
                        console.log(`\n  ✓ 数据量变化: ${lastCount} → ${status.count} 条`);
                        noChangeStartTime = null;
                    }
                }
            } else {
                // 没有"加载更多"按钮，说明数据已经全部加载完成，直接结束
                console.log(`  ✓ 数据加载完成 (${status.count} 条，无"加载更多"按钮)`);
                break;
            }
            // 更新上一次的数据量
            lastCount = status.count;

            // 如果有"加载更多"按钮的位置信息
            if (status.pos) {
                process.stdout.write(`  ⏳ 点击"加载更多"... `);
                // 使用鼠标点击按钮
                await page.mouse.click(status.pos.x, status.pos.y);

                // 智能等待：每秒检测数据量和加载状态
                let waitTime = 0;
                const maxWait = 30;

                // 最多等待30秒
                while (waitTime < maxWait) {
                    await new Promise(r => setTimeout(r, 1000));
                    waitTime++;

                    // 检查新的状态
                    const newStatus = await page.evaluate(() => {
                        const match = document.body.innerText.match(/当前页\s*(\d+)\s*个商品/);
                        const count = match ? parseInt(match[1]) : 0;

                        // 检查是否还有"加载更多"按钮
                        const elms = Array.from(document.querySelectorAll('button, div, span'));
                        const loadBtn = elms.find(e =>
                            e.innerText && e.innerText.trim() === '加载更多' &&
                            e.offsetParent !== null && e.children.length === 0
                        );

                        const finished = document.body.innerText.includes('没有更多了');

                        return { count, hasBtn: !!loadBtn, finished };
                    });

                    // 如果数据量增长了，显示并继续
                    if (newStatus.count > status.count) {
                        console.log(`✓ 数据增长 (${status.count} → ${newStatus.count})`);
                        break; // 跳出等待循环
                    }

                    // 如果"加载更多"按钮消失，开始30秒倒计时
                    if (!newStatus.hasBtn || newStatus.finished) {
                        if (!newStatus.hasBtn) {
                            // 按钮消失，开始等待30秒
                            if (waitTime >= 30) {
                                console.log(`✓ 数据加载完成 (${newStatus.count} 条，"加载更多"按钮已消失且等待30秒)`);
                                return; // 返回到外层循环
                            }
                            // 继续等待直到30秒
                            process.stdout.write(`\r  ⏳ 按钮已消失，等待确认 (${waitTime}/30s)...   `);
                        } else {
                            // 出现"没有更多了"
                            console.log(`✓ 数据加载完成 (${newStatus.count} 条，检测到"没有更多了")`);
                            return; // 返回到外层循环
                        }
                    } else {
                        // 按钮还在，继续等待
                        process.stdout.write(`\r  ⏳ 等待加载 (${waitTime}/${maxWait}s)...   `);
                    }
                }

                // 清除进度显示
                process.stdout.write('\r' + ' '.repeat(50) + '\r');
            } else {
                // 没有"加载更多"按钮，说明数据已经全部加载完成
                console.log(`  ✓ 数据加载完成 (${status.count} 条，无"加载更多"按钮)`);
                break;
            }
        }

        // ========================================
        // 第一阶段结束后的30秒等待
        // 在等待过程中持续监控是否出现"加载更多"按钮
        // ========================================
        console.log('\n[*] 第一阶段完成，等待30秒确保数据完全加载...');
        console.log('[*] 等待期间会持续监控"加载更多"按钮...');

        let waitCount = 0;           // 已等待秒数
        const maxWait = 30;          // 最多等待30秒
        let lastDataCount = 0;       // 上一次的数据量

        // 获取初始数据量
        lastDataCount = await page.evaluate(() => {
            const match = document.body.innerText.match(/加载数据\s*(\d+)\s*条/);
            return match ? parseInt(match[1]) : 0;
        });

        // 循环等待，最多30秒
        while (waitCount < maxWait) {
            await new Promise(r => setTimeout(r, 1000));
            waitCount++;

            // 每秒检查是否有"加载更多"按钮出现
            const status = await page.evaluate(() => {
                const match = document.body.innerText.match(/加载数据\s*(\d+)\s*条/);
                const count = match ? parseInt(match[1]) : 0;

                // 检查是否还有"加载更多"按钮
                const elms = Array.from(document.querySelectorAll('button, div, span'));
                const loadBtn = elms.find(e =>
                    e.innerText && e.innerText.trim() === '加载更多' &&
                    e.offsetParent !== null && e.children.length === 0
                );

                let pos = null;
                if (loadBtn) {
                    loadBtn.scrollIntoView({ behavior: 'smooth', block: 'center' });
                    const r = loadBtn.getBoundingClientRect();
                    pos = { x: r.left + r.width / 2, y: r.top + r.height / 2 };

                    // 给按钮加上红色高亮
                    const prevOutline = loadBtn.style.outline;
                    const prevBoxShadow = loadBtn.style.boxShadow;
                    loadBtn.style.outline = '3px solid red';
                    loadBtn.style.boxShadow = '0 0 10px 3px red';
                    setTimeout(() => {
                        loadBtn.style.outline = prevOutline;
                        loadBtn.style.boxShadow = prevBoxShadow;
                    }, 60000);
                }

                return {
                    count,
                    hasBtn: !!loadBtn,
                    pos
                };
            });

            // 如果数据量有变化，重置等待计数
            if (status.count > lastDataCount) {
                console.log(`\n[✓] 检测到新数据: ${lastDataCount} → ${status.count} 条，重置等待计时`);
                lastDataCount = status.count;
                waitCount = 0; // 重置计数
                process.stdout.write(`\r[*] 等待确认 (重置 ${waitCount}/${maxWait}秒)...   `);
                continue; // 继续下一轮循环
            }

            // 如果出现"加载更多"按钮，点击它
            if (status.hasBtn) {
                console.log(`\n[✓] 检测到"加载更多"按钮，正在点击...`);
                process.stdout.write(`  ⏳ 点击"加载更多"... `);

                // 点击按钮
                await page.mouse.click(status.pos.x, status.pos.y);

                // 等待数据加载
                let loadWaitTime = 0;
                while (loadWaitTime < 30) {
                    await new Promise(r => setTimeout(r, 1000));
                    loadWaitTime++;

                    const newStatus = await page.evaluate(() => {
                        const match = document.body.innerText.match(/当前页\s*(\d+)\s*个商品/);
                        const count = match ? parseInt(match[1]) : 0;

                        const elms = Array.from(document.querySelectorAll('button, div, span'));
                        const loadBtn = elms.find(e =>
                            e.innerText && e.innerText.trim() === '加载更多' &&
                            e.offsetParent !== null && e.children.length === 0
                        );

                        return { count, hasBtn: !!loadBtn };
                    });

                    // 如果数据量增长了
                    if (newStatus.count > status.count) {
                        console.log(`✓ 数据增长 (${status.count} → ${newStatus.count})`);
                        lastDataCount = newStatus.count;
                        waitCount = 0; // 重置等待计数
                        break;
                    }

                    // 如果按钮消失
                    if (!newStatus.hasBtn) {
                        console.log(`✓ "加载更多"按钮已消失`);
                        break;
                    }

                    // 显示等待进度
                    process.stdout.write(`\r  ⏳ 等待加载 (${loadWaitTime}/30s)...   `);
                }

                // 清除进度显示
                process.stdout.write('\r' + ' '.repeat(50) + '\r');
            } else {
                // 没有按钮，继续等待
                process.stdout.write(`\r[*] 等待确认 (${waitCount}/${maxWait}秒)...   `);
            }
        }

        // 清除进度显示
        process.stdout.write('\r' + ' '.repeat(50) + '\r');
        console.log(`[√] 30秒等待完成，当前数据量: ${lastDataCount} 条`);

        // ========================================
        // 第二阶段：一次性导出全部数据
        // ========================================
        console.log('\n' + '='.repeat(60));
        console.log('[3/3] 第二阶段：导出全部数据');
        console.log('='.repeat(60));

        // 检查当前数据量
        const currentCount = await page.evaluate(() => {
            const match = document.body.innerText.match(/加载数据\s*(\d+)\s*条/);
            return match ? parseInt(match[1]) : 0;
        });

        if (currentCount === 0) {
            console.log('\n[!] 没有数据需要导出');
        } else {
            console.log(`\n📊 当前数据量: ${currentCount} 条`);

            // ===== 步骤1: 点击"全选"按钮 =====
            console.log('\n[*] 步骤1: 点击全选按���');
            process.stdout.write('  ⏳ 正在查找并点击全选按钮... ');

            const selectAllResult = await page.evaluate(() => {
                // 查找"全选"按钮的多种可能方式
                const buttons = Array.from(document.querySelectorAll('button, div, span, a, label'));

                // 方法1: 通过文字查找"全选"
                let selectAllBtn = buttons.find(btn => {
                    const text = btn.innerText && btn.innerText.trim();
                    return (text === '全选' || text === '选中全部' || text === 'Select All') &&
                           btn.offsetParent !== null;
                });

                // 方法2: 查找表头的复选框（通常在表格第一行）
                if (!selectAllBtn) {
                    const headerCheckbox = document.querySelector('table thead input[type="checkbox"], table tbody tr:first-child input[type="checkbox"]');
                    if (headerCheckbox && headerCheckbox.offsetParent !== null) {
                        selectAllBtn = headerCheckbox;
                    }
                }

                // 方法3: 查找包含"全选"文字的label
                if (!selectAllBtn) {
                    const labels = Array.from(document.querySelectorAll('label'));
                    selectAllBtn = labels.find(lbl => {
                        const text = lbl.innerText && lbl.innerText.trim();
                        return (text.includes('全选') || text.includes('选中全部')) && lbl.offsetParent !== null;
                    });
                }

                if (selectAllBtn) {
                    // 滚动到按钮位置
                    selectAllBtn.scrollIntoView({ behavior: 'smooth', block: 'center' });

                    // 给按钮加红色高亮
                    const prevOutline = selectAllBtn.style.outline;
                    const prevBoxShadow = selectAllBtn.style.boxShadow;
                    selectAllBtn.style.outline = '3px solid red';
                    selectAllBtn.style.boxShadow = '0 0 10px 3px red';

                    // 点击按钮
                    selectAllBtn.click();

                    // 5秒后恢复样式
                    setTimeout(() => {
                        selectAllBtn.style.outline = prevOutline;
                        selectAllBtn.style.boxShadow = prevBoxShadow;
                    }, 5000);

                    return { success: true, text: selectAllBtn.innerText || '全选按钮' };
                }

                return { success: false, text: null };
            });

            if (selectAllResult.success) {
                console.log(`✓ 已点击全选按钮 (${selectAllResult.text})`);
            } else {
                console.log('✗ 未找到全选按钮');
            }

            // 等待3秒让选择生效
            await new Promise(r => setTimeout(r, 3000));

            // ===== 步骤2: 导出全部数据 =====
            console.log('\n[*] 步骤2: 导出全部数据');
            process.stdout.write('  ⏳ 正在查找并点击导出按钮... ');

            const exportAllResult = await page.evaluate(() => {
                // 查找"导出"或"导出全部"按钮
                const buttons = Array.from(document.querySelectorAll('button, div, span, a'));
                const exportBtn = buttons.find(btn => {
                    const text = btn.innerText && btn.innerText.trim();
                    return (text === '导出' || text === '导出全部' || text === 'Export' || text === '导出数据') &&
                           btn.offsetParent !== null;
                });

                if (exportBtn) {
                    // 滚动到按钮位置
                    exportBtn.scrollIntoView({ behavior: 'smooth', block: 'center' });

                    // 给按钮加红色高亮
                    const prevOutline = exportBtn.style.outline;
                    const prevBoxShadow = exportBtn.style.boxShadow;
                    exportBtn.style.outline = '3px solid red';
                    exportBtn.style.boxShadow = '0 0 10px 3px red';

                    // 点击按钮
                    exportBtn.click();

                    // 5秒后恢复样式
                    setTimeout(() => {
                        exportBtn.style.outline = prevOutline;
                        exportBtn.style.boxShadow = prevBoxShadow;
                    }, 5000);

                    return { success: true, text: exportBtn.innerText };
                }

                return { success: false, text: null };
            });

            if (exportAllResult.success) {
                console.log(`✓ 已点击导出按钮 (${exportAllResult.text})`);
            } else {
                console.log('✗ 未找到导出按钮');
            }

            // ===== 步骤3: 等待文件下载并校验 =====
            console.log('\n[*] 步骤3: 等待文件下载');

            // 记录下载前的文件列表
            const beforeDownloadFiles = fs.readdirSync(downloadPath);

            // 根据数据量动态计算等待时间（每条数据约0.5秒，最少30秒，最多120秒）
            const waitTime = Math.max(30, Math.min(120, Math.ceil(currentCount / 2)));
            console.log(`  📊 根据 ${currentCount} 条数据，预计等待 ${waitTime} 秒...`);

            // 循环等待并检测新文件
            let newFileDetected = false;

            for (let i = 1; i <= waitTime; i++) {
                await new Promise(r => setTimeout(r, 1000));

                // 每5秒检查一次是否有新文件
                if (i % 5 === 0) {
                    const afterDownloadFiles = fs.readdirSync(downloadPath);
                    const newFiles = afterDownloadFiles.filter(f => !beforeDownloadFiles.includes(f));

                    if (newFiles.length > 0) {
                        newFileDetected = true;
                        detectedTime = i;
                        process.stdout.write(`\r  ⏳ 检测到新文件！继续等待确保下载完成... (${i}/${waitTime}秒)     `);
                        break; // 检测到文件后退出检查循环，继续等待
                    }

                    process.stdout.write(`\r  ⏳ 等待文件下载 (${i}/${waitTime}秒)...     `);
                } else {
                    process.stdout.write(`\r  ⏳ 等待文件下载 (${i}/${waitTime}秒)...     `);
                }
            }

            // 如果检测到新文件，再额外等待3秒确保下载完整
            if (newFileDetected) {
                console.log('\n  ✓ 检测到新文件，额外等待3秒确保下载完成...');
                for (let i = 1; i <= 3; i++) {
                    await new Promise(r => setTimeout(r, 1000));
                    process.stdout.write(`\r  ⏳ 确认下载完成 (${i}/3秒)...     `);
                }
                console.log('\n  ✓ 下载等待完成');
            } else {
                console.log('\n  ⚠ 警告: 未检测到新文件');
            }

            process.stdout.write('\r' + ' '.repeat(60) + '\r');

            // 最终检查下载文件夹中的新文件
            const afterDownloadFiles = fs.readdirSync(downloadPath);
            const newFiles = afterDownloadFiles.filter(f => !beforeDownloadFiles.includes(f));

            // 校验下载结果
            if (newFiles.length > 0) {
                console.log(`  ✓ 检测到新文件: ${newFiles.length} 个`);
                newFiles.forEach(f => {
                    console.log(`    - ${f}`);
                });

                // 检查Excel文件内容，获取实际数据行数
                let excelRowCount = 0;
                const excelFiles = newFiles.filter(f => f.endsWith('.xlsx') || f.endsWith('.xls'));

                if (excelFiles.length > 0) {
                    console.log('  📊 正在读取Excel文件统计数据行数...');

                    // 读取Excel文件获取真实行数
                    for (const excelFile of excelFiles) {
                        const filePath = path.join(downloadPath, excelFile);

                        try {
                            // 使用 xlsx 库读取文件
                            const workbook = XLSX.readFile(filePath);

                            // 获取第一个工作表
                            const firstSheetName = workbook.SheetNames[0];
                            const worksheet = workbook.Sheets[firstSheetName];

                            // 将工作表转换为JSON数据
                            const jsonData = XLSX.utils.sheet_to_json(worksheet);

                            // 统计数据行数（不包括表头）
                            const rowCount = jsonData.length;

                            // 获取文件大小
                            const stats = fs.statSync(filePath);
                            const fileSizeKB = (stats.size / 1024).toFixed(2);

                            console.log(`    - ${excelFile} (${fileSizeKB} KB): ${rowCount} 条数据`);

                            excelRowCount += rowCount;
                        } catch (e) {
                            console.log(`    - ${excelFile}: 读取失败 (${e.message})`);
                        }
                    }

                    console.log(`  📊 实际导出数据量: ${excelRowCount} 条`);
                }

                // 比较导出数量与下载文件数量
                if (excelFiles.length > 0) {
                    if (excelRowCount >= currentCount * 0.9) {
                        // 允许10%的误差范围
                        console.log(`  ✓✓✓ 文件校验通过 (数据 ${currentCount} 条，文件实际 ${excelRowCount} 条)`);
                        console.log('  ✓✓✓ 导出成功！可以关闭浏览器了');

                        // 成功导出，设置标志
                        exportSuccess = true;
                    } else {
                        const matchRate = ((excelRowCount / currentCount) * 100).toFixed(1);
                        console.log(`  ⚠⚠⚠ 警告: 文件数据量不足 (数据 ${currentCount} 条，文件实际 ${excelRowCount} 条，匹配率 ${matchRate}%)`);
                        console.log('  ⚠⚠⚠ 建议手动检查导出结果，浏览器将保持打开');

                        // 导出可能失败，保持浏览器打开
                        exportSuccess = false;
                    }
                } else {
                    console.log('  ⚠⚠⚠ 警告: 未找到Excel文件，可能导出失败');
                    console.log('  ⚠⚠⚠ 浏览器将保持打开以便检查');

                    // 没有Excel文件，保持浏览器打开
                    exportSuccess = false;
                }
            } else {
                console.log('  ⚠⚠⚠ 严重警告: 未检测到任何新文件下载');
                console.log('  ⚠⚠⚠ 导出可能失败，浏览器将保持打开以便检查');

                // 完全没有文件，保持浏览器打开
                exportSuccess = false;
            }

            console.log('\n' + '='.repeat(60));
            if (exportSuccess) {
                console.log('✓✓✓ 导出成功！浏览器即将关闭...');
            } else {
                console.log('⚠⚠⚠ 导出可能失败，浏览器将保持打开');
                console.log('⚠⚠⚠ 请手动检查浏览器中的导出结果');
            }
            console.log('='.repeat(60));
        }

        console.log('\n' + '='.repeat(60));
        console.log('✓ 任务完成！请检查 downloads_asin 文件夹中的导出文件');
        console.log('='.repeat(60));

    } catch (err) {
        // 捕获并显示错误
        console.error('\n[!] 报错: ' + err.message);
    } finally {
        // 根据导出结果决定是否关闭浏览器
        if (browser) {
            // 只有在导出成功时才关闭浏览器
            if (exportSuccess) {
                console.log('[*] 正在关闭浏览器...');
                try {
                    // 关闭浏览器（不仅仅是断开连接）
                    await browser.close();
                    console.log('[√] 浏览器已关闭');
                } catch (e) {
                    // 如果关闭失败，尝试只断开连接
                    await browser.disconnect();
                    console.log('[√] 已断开浏览器连接');
                }
            } else {
                // 导出可能失败，保持浏览器打开
                console.log('[*] 导出可能失败，浏览器将保持打开');
                console.log('[*] 请手动检查浏览器中的导出结果');
                console.log('[*] 检查完成后，可以手动关闭浏览器');
                // 只断开连接，不关闭浏览器
                try {
                    await browser.disconnect();
                    console.log('[√] 已断开自动化连接，浏览器保持打开');
                } catch (e) {
                    console.log('[!] 断开连接失败');
                }
            }
        }
        // 退出程序
        process.exit();
    }
})();
// ==================== 主程序结束 ====================
