---
name: personal-coding-standards
description: 在执行任何编码任务时使用此 skill，确保遵循用户的个人编码习惯和工作流程要求
---

# 个人编码标准和工作流程

## When to use this skill

**必须在以下情况下使用此 skill：**
- 用户请求编写、修改或重构任何代码
- 用户请求实现新功能
- 用户请求修复 bug
- 用户请求进行代码审查
- 任何涉及代码变更的任务

**重要：此 skill 应该在每次编码任务开始时自动应用，无需用户明确调用。**

---

## 核心工作流程（必须严格遵循）

### 阶段 1：需求理解和头脑风暴

在开始任何编码工作之前，**必须**先进行头脑风暴：

1. **理解需求**
   - 仔细分析用户的需求
   - 识别潜在的边界情况和约束条件
   - 明确成功标准

2. **技术方案设计**
   - 考虑多种实现方案
   - 评估每种方案的优缺点
   - 选择最符合用户编码标准的方案

3. **任务规划**
   - 将任务拆分成尽可能细粒度的子任务
   - 每个子任务应该是独立的、可测试的、可回滚的
   - 使用 TodoWrite 工具创建详细的任务清单
   - 任务粒度要足够细，方便 debug 和回滚

4. **确认方案**
   - 向用户展示规划的方案和任务清单
   - 确保方案符合用户要求后再开始实施

### 阶段 2：测试驱动开发（TDD）

**关键原则：测试先行，代码后行**

1. **编写测试用例**
   - 在编写任何实现代码之前，先编写测试
   - 测试应该覆盖：
     - 正常情况
     - 边界情况
     - 异常情况
     - 错误处理

2. **测试文件组织**
   - 为每个模块/类/函数创建对应的测试文件
   - 测试文件命名清晰，易于识别

3. **运行测试**
   - 确保新测试最初是失败的（红灯）
   - 这验证了测试确实在测试新功能

### 阶段 3：实现代码

1. **版本控制准备**
   - 在开始实现前，确保当前代码已提交到 git
   - 创建清晰的 commit 记录作为回滚点
   - 考虑使用 git branch 进行功能开发

2. **编写实现代码**
   - 遵循下面的编码标准
   - 每完成一个小的功能点就运行测试
   - 保持小步迭代

3. **迭代验证**
   - 每次代码变更后立即运行测试
   - **测试必须通过才能继续下一步**
   - 如果测试失败：
     - 分析失败原因
     - 修复代码或修正测试
     - 如果无法快速修复，使用 `git reset --hard` 或 `git checkout` 回滚到上一个稳定版本
     - 重新规划实现方案

### 阶段 4：完成和验证

1. **最终测试**
   - 运行完整的测试套件
   - 确保所有测试通过
   - 检查测试覆盖率

2. **代码审查**
   - 自我审查代码质量
   - 确保符合所有编码标准
   - 检查是否有遗漏的注释或文档

3. **提交代码**
   - 编写清晰的 commit message
   - 说明做了什么改动和为什么

---

## 编码标准（必须遵循）

### 1. 代码注释规范

**注释语言：所有注释必须使用中文**

**注释详细程度：详细注释**

```python
# Python 示例
class UserService:
    """
    用户服务类

    负责处理所有与用户相关的业务逻辑，包括用户注册、登录、
    信息更新等操作。

    Attributes:
        db: 数据库连接对象
        logger: 日志记录器
    """

    def __init__(self, db, logger):
        """
        初始化用户服务

        Args:
            db: 数据库连接对象，用于执行数据库操作
            logger: 日志记录器，用于记录操作日志
        """
        self.db = db
        self.logger = logger

    def register_user(self, username, email, password):
        """
        注册新用户

        执行用户注册流程，包括验证输入、检查用户是否已存在、
        加密密码、保存到数据库等步骤。

        Args:
            username (str): 用户名，长度必须在 3-20 个字符之间
            email (str): 电子邮件地址，必须是有效的邮箱格式
            password (str): 密码，长度必须至少 8 个字符

        Returns:
            dict: 包含用户信息的字典，格式为：
                {
                    'id': 用户ID,
                    'username': 用户名,
                    'email': 邮箱,
                    'created_at': 创建时间
                }

        Raises:
            ValueError: 当输入参数不符合要求时
            UserExistsError: 当用户名或邮箱已被注册时
            DatabaseError: 当数据库操作失败时
        """
        # 验证输入参数的有效性
        self._validate_registration_input(username, email, password)

        # 检查用户名是否已存在
        # 这一步很重要，避免重复注册
        if self._user_exists(username, email):
            self.logger.warning(f"注册失败：用户名 {username} 或邮箱 {email} 已存在")
            raise UserExistsError("用户名或邮箱已被注册")

        # 加密密码
        # 使用 bcrypt 算法进行加密，确保密码安全
        hashed_password = self._hash_password(password)

        # 保存用户到数据库
        try:
            user = self.db.create_user(
                username=username,
                email=email,
                password=hashed_password
            )
            self.logger.info(f"用户注册成功：{username}")
            return user
        except Exception as e:
            # 数据库操作失败，记录错误并抛出
            self.logger.error(f"用户注册失败：{str(e)}")
            raise DatabaseError(f"注册用户时发生数据库错误：{str(e)}")
```

```javascript
// JavaScript/TypeScript 示例
/**
 * 用户服务类
 *
 * 负责处理所有与用户相关的业务逻辑，包括用户注册、登录、
 * 信息更新等操作。
 */
class UserService {
    /**
     * 初始化用户服务
     *
     * @param {Object} db - 数据库连接对象，用于执行数据库操作
     * @param {Object} logger - 日志记录器，用于记录操作日志
     */
    constructor(db, logger) {
        this.db = db;
        this.logger = logger;
    }

    /**
     * 注册新用户
     *
     * 执行用户注册流程，包括验证输入、检查用户是否已存在、
     * 加密密码、保存到数据库等步骤。
     *
     * @param {string} username - 用户名，长度必须在 3-20 个字符之间
     * @param {string} email - 电子邮件地址，必须是有效的邮箱格式
     * @param {string} password - 密码，长度必须至少 8 个字符
     * @returns {Promise<Object>} 包含用户信息的对象
     * @throws {ValueError} 当输入参数不符合要求时
     * @throws {UserExistsError} 当用户名或邮箱已被注册时
     * @throws {DatabaseError} 当数据库操作失败时
     */
    async registerUser(username, email, password) {
        // 验证输入参数的有效性
        this._validateRegistrationInput(username, email, password);

        // 检查用户名是否已存在
        // 这一步很重要，避免重复注册
        if (await this._userExists(username, email)) {
            this.logger.warning(`注册失败：用户名 ${username} 或邮箱 ${email} 已存在`);
            throw new UserExistsError('用户名或邮箱已被注册');
        }

        // 加密密码
        // 使用 bcrypt 算法进行加密，确保密码安全
        const hashedPassword = await this._hashPassword(password);

        // 保存用户到数据库
        try {
            const user = await this.db.createUser({
                username,
                email,
                password: hashedPassword
            });
            this.logger.info(`用户注册成功：${username}`);
            return user;
        } catch (error) {
            // 数据库操作失败，记录错误并抛出
            this.logger.error(`用户注册失败：${error.message}`);
            throw new DatabaseError(`注册用户时发生数据库错误：${error.message}`);
        }
    }
}
```

**注释要求：**
- 每个类必须有类级别的文档注释
- 每个公共方法必须有详细的文档注释
- 复杂的逻辑块必须有行内注释说明
- 关键算法和业务逻辑必须有注释解释"为什么"这样做
- 所有注释必须使用中文

### 2. 错误处理规范

**原则：详细的异常处理 + 日志记录 + 用户友好提示**

```python
# Python 示例
import logging

class PaymentService:
    def process_payment(self, user_id, amount):
        """
        处理支付请求

        Args:
            user_id (int): 用户ID
            amount (float): 支付金额

        Returns:
            dict: 支付结果

        Raises:
            ValueError: 参数无效
            InsufficientFundsError: 余额不足
            PaymentGatewayError: 支付网关错误
        """
        try:
            # 验证输入参数
            if amount <= 0:
                error_msg = "支付金额必须大于0"
                logging.warning(f"支付参数验证失败：用户 {user_id}，金额 {amount}")
                raise ValueError(error_msg)

            # 检查用户余额
            try:
                balance = self._get_user_balance(user_id)
            except DatabaseError as e:
                # 数据库查询失败
                logging.error(f"查询用户余额失败：用户 {user_id}，错误：{str(e)}")
                raise PaymentError("抱歉，系统暂时无法处理您的支付请求，请稍后重试")

            if balance < amount:
                # 余额不足
                logging.info(f"支付失败：用户 {user_id} 余额不足，当前余额 {balance}，需要 {amount}")
                raise InsufficientFundsError(
                    f"您的账户余额不足。当前余额：¥{balance:.2f}，需要支付：¥{amount:.2f}"
                )

            # 调用支付网关
            try:
                result = self._call_payment_gateway(user_id, amount)
                logging.info(f"支付成功：用户 {user_id}，金额 {amount}，交易ID {result['transaction_id']}")
                return {
                    'success': True,
                    'message': '支付成功！',
                    'transaction_id': result['transaction_id']
                }
            except PaymentGatewayError as e:
                # 支付网关错误
                logging.error(f"支付网关错误：用户 {user_id}，金额 {amount}，错误：{str(e)}")
                raise PaymentError(
                    "抱歉，支付处理失败，您的账户未被扣款。请稍后重试或联系客服。"
                )

        except ValueError as e:
            # 参数验证错误，直接向用户展示错误信息
            raise
        except InsufficientFundsError as e:
            # 余额不足，直接向用户展示错误信息
            raise
        except PaymentError as e:
            # 支付错误，直接向用户展示错误信息
            raise
        except Exception as e:
            # 未预期的错误，记录详细日志，向用户展示友好信息
            logging.critical(f"支付处理发生未预期错误：用户 {user_id}，金额 {amount}，错误：{str(e)}", exc_info=True)
            raise PaymentError(
                "抱歉，系统发生错误，请稍后重试。如果问题持续存在，请联系客服。"
            )
```

```javascript
// JavaScript/TypeScript 示例
class PaymentService {
    async processPayment(userId, amount) {
        try {
            // 验证输入参数
            if (amount <= 0) {
                const errorMsg = '支付金额必须大于0';
                logger.warning(`支付参数验证失败：用户 ${userId}，金额 ${amount}`);
                throw new ValueError(errorMsg);
            }

            // 检查用户余额
            let balance;
            try {
                balance = await this._getUserBalance(userId);
            } catch (error) {
                // 数据库查询失败
                logger.error(`查询用户余额失败：用户 ${userId}，错误：${error.message}`);
                throw new PaymentError('抱歉，系统暂时无法处理您的支付请求，请稍后重试');
            }

            if (balance < amount) {
                // 余额不足
                logger.info(`支付失败：用户 ${userId} 余额不足，当前余额 ${balance}，需要 ${amount}`);
                throw new InsufficientFundsError(
                    `您的账户余额不足。当前余额：¥${balance.toFixed(2)}，需要支付：¥${amount.toFixed(2)}`
                );
            }

            // 调用支付网关
            try {
                const result = await this._callPaymentGateway(userId, amount);
                logger.info(`支付成功：用户 ${userId}，金额 ${amount}，交易ID ${result.transactionId}`);
                return {
                    success: true,
                    message: '支付成功！',
                    transactionId: result.transactionId
                };
            } catch (error) {
                // 支付网关错误
                logger.error(`支付网关错误：用户 ${userId}，金额 ${amount}，错误：${error.message}`);
                throw new PaymentError(
                    '抱歉，支付处理失败，您的账户未被扣款。请稍后重试或联系客服。'
                );
            }

        } catch (error) {
            // 根据错误类型处理
            if (error instanceof ValueError ||
                error instanceof InsufficientFundsError ||
                error instanceof PaymentError) {
                // 已知错误，直接抛出
                throw error;
            } else {
                // 未预期的错误，记录详细日志，向用户展示友好信息
                logger.critical(
                    `支付处理发生未预期错误：用户 ${userId}，金额 ${amount}，错误：${error.message}`,
                    { stack: error.stack }
                );
                throw new PaymentError(
                    '抱歉，系统发生错误，请稍后重试。如果问题持续存在，请联系客服。'
                );
            }
        }
    }
}
```

**错误处理要求：**
- 每个可能出错的操作都要有 try-catch 包裹
- 所有错误都要记录到日志系统，包含足够的上下文信息
- 日志级别要合理使用：
  - `DEBUG`: 调试信息
  - `INFO`: 正常操作信息
  - `WARNING`: 警告信息（如参数验证失败）
  - `ERROR`: 错误信息（如外部服务调用失败）
  - `CRITICAL`: 严重错误（如未预期的异常）
- 向用户展示的错误信息必须友好、清晰、可操作
- 不要向用户暴露技术细节或敏感信息
- 为不同类型的错误创建自定义异常类

### 3. 代码组织规范

**原则：模块化 + 简洁实用 + 面向对象**

**模块化要求：**
- 每个模块只负责一个明确的功能领域
- 模块之间通过清晰的接口通信
- 避免循环依赖
- 使用依赖注入提高可测试性

**面向对象要求：**
- 使用类来组织相关的数据和行为
- 遵循 SOLID 原则：
  - 单一职责原则（SRP）
  - 开闭原则（OCP）
  - 里氏替换原则（LSP）
  - 接口隔离原则（ISP）
  - 依赖倒置原则（DIP）
- 合理使用继承和组合
- 使用抽象类和接口定义契约

**简洁实用要求：**
- 避免过度设计
- 不要为了设计模式而使用设计模式
- 代码要易读、易维护
- 优先选择简单直接的解决方案
- 只在真正需要时才引入抽象

**目录结构示例：**

```
project/
├── src/
│   ├── models/          # 数据模型
│   ├── services/        # 业务逻辑服务
│   ├── repositories/    # 数据访问层
│   ├── controllers/     # 控制器（如果是 Web 应用）
│   ├── utils/           # 工具函数
│   └── config/          # 配置文件
├── tests/               # 测试文件（镜像 src 结构）
│   ├── models/
│   ├── services/
│   └── repositories/
├── docs/                # 文档
└── scripts/             # 脚本工具
```

### 4. Git 版本管理规范

**分支策略：**
- `main/master`: 主分支，始终保持可部署状态
- `develop`: 开发分支
- `feature/*`: 功能分支
- `bugfix/*`: 修复分支
- `hotfix/*`: 紧急修复分支

**Commit 规范：**
- 使用清晰的 commit message
- 格式：`<type>: <subject>`
- Type 类型：
  - `feat`: 新功能
  - `fix`: 修复 bug
  - `refactor`: 重构
  - `test`: 添加测试
  - `docs`: 文档更新
  - `style`: 代码格式调整
  - `chore`: 构建/工具变动

**回滚策略：**
- 每个小功能完成后立即 commit
- 测试失败时使用 `git reset --hard HEAD` 回滚到上一个稳定版本
- 重要节点使用 `git tag` 标记
- 使用 `git stash` 临时保存未完成的工作

---

## 工作流程检查清单

在执行任何编码任务时，必须按照以下清单进行：

### ✅ 开始前
- [ ] 理解用户需求
- [ ] 进行头脑风暴，设计技术方案
- [ ] 将任务拆分成细粒度的子任务
- [ ] 使用 TodoWrite 创建详细的任务清单
- [ ] 向用户确认方案

### ✅ 实现中
- [ ] 确保当前代码已提交到 git（作为回滚点）
- [ ] 先编写测试用例
- [ ] 运行测试，确保测试失败（红灯）
- [ ] 编写实现代码
- [ ] 运行测试，确保测试通过（绿灯）
- [ ] 如果测试失败，修复或回滚
- [ ] 添加详细的中文注释
- [ ] 实现完整的错误处理和日志记录
- [ ] 确保错误信息对用户友好
- [ ] 提交代码到 git

### ✅ 完成后
- [ ] 运行完整的测试套件
- [ ] 所有测试必须通过
- [ ] 代码审查（检查注释、错误处理、代码组织）
- [ ] 更新文档（如果需要）
- [ ] 最终提交

---

## 示例工作流程

<example>
用户: 帮我实现一个用户注册功能

助手: 好的，我来帮你实现用户注册功能。让我先进行头脑风暴和任务规划。

**需求分析：**
用户注册功能需要包含：
1. 输入验证（用户名、邮箱、密码）
2. 检查用户是否已存在
3. 密码加密
4. 保存到数据库
5. 错误处理和日志记录
6. 返回友好的提示信息

**技术方案：**
- 使用面向对象的方式组织代码，创建 UserService 类
- 使用 bcrypt 进行密码加密
- 实现详细的异常处理和日志记录
- 所有注释使用中文

**任务拆分：**
[使用 TodoWrite 创建任务清单]
1. 创建 UserService 类的测试文件
2. 编写用户注册功能的测试用例
3. 实现 UserService 类的基本结构
4. 实现输入验证逻辑
5. 实现用户存在性检查
6. 实现密码加密
7. 实现数据库保存
8. 实现错误处理和日志记录
9. 运行测试并确保通过
10. 代码审查和提交

这个方案符合你的要求吗？

[等待用户确认后开始实施]

[实施过程中严格遵循 TDD 流程，每个步骤都先写测试，再写实现，确保测试通过后才继续]
</example>

---

## 重要提醒

1. **测试先行是强制要求**：任何实现代码之前必须先有测试
2. **测试不通过不能继续**：如果测试失败，必须修复或回滚
3. **任务拆分要细**：越细越好，方便 debug 和回滚
4. **Git 是安全网**：频繁提交，随时可以回滚
5. **注释必须详细且使用中文**：让代码易于理解和维护
6. **错误处理必须完整**：包括日志记录和用户友好提示
7. **代码组织要清晰**：模块化、面向对象、简洁实用

---

## 适用语言

此标准适用于所有编程语言，包括但不限于：
- Python
- JavaScript/TypeScript
- Java
- C#
- Go
- Rust
- 等等

根据具体语言的特性和惯例进行适当调整，但核心原则保持不变。
