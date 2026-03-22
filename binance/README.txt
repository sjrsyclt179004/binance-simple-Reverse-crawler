币安跟单数据采集程序使用说明
1. 程序启动采集步骤
1.1 前置准备

1.1.1 环境验证
确保本地安装 Python 3.8 版本，打开终端执行以下命令验证版本：
bash
运行
python --version  # 输出需包含「Python 3.8.x」

1.1.2 安装依赖
执行以下命令安装程序必备的第三方库，确保版本适配 Python 3.8：
bash
运行
pip install requests==2.31.0 pymysql==1.1.0 urllib3==2.0.7

1.1.3 数据库准备
确认 MySQL 8.0.44 服务已正常启动；
执行配套的建表 SQL 脚本，完成binance数据库及三张核心数据表的创建。

1.1.4 核心配置调整（必须修改）
打开采集程序文件，定位到开头=========== 配置项 ============区域，修改以下核心配置：
MySQL 密码（DB_CONFIG 的 password）	替换为实际 MySQL 登录密码
（需要有VPN地址）代理地址（PROXY）	有代理则填写实际地址，无代理必须设置为 None	PROXY = {'http':'http://127.0.0.1:7897'}（无代理场景）	无代理：PROXY = None；有代理：PROXY = {'http':'http://192.168.1.100:1080','https':'http://192.168.1.100:1080'}

1.2 启动采集
方式 1：命令行启动（推荐）
将采集程序保存为binance_collector.py；
打开终端 / 命令提示符，切换到程序所在文件夹；
执行启动命令：
bash
运行
python binance_collector.py
查看终端输出判断运行状态：
正常状态：依次显示「开始采集」「成功保存交易员」「采集完成」等日志；
异常排查：提示「数据库连接失败」优先检查 MySQL 密码；提示「请求超时」优先检查代理地址。
方式 2：IDE 直接运行
使用 PyCharm、VS Code 等 IDE 打开binance_collector.py文件；
点击 IDE 界面的「运行」按钮启动程序；
通过控制台输出确认采集状态。
1.3 采集终止
命令行启动场景：按下Ctrl + C组合键终止采集；
IDE 启动场景：点击 IDE 界面的「停止」按钮终止采集。

2. 数据表结构说明
2.1 核心数据表信息

lead_trader	存储交易员基础信息	
lead_id（交易员唯一 ID）
nickname（昵称）
aum（资产管理规模）	重复采集会自动更新数据
lead_position_current	存储交易员未平仓的当前持仓	
lead_id（关联交易员）
symbol（交易对）
side（多空方向）
unrealized_pnl（未实现盈亏）	仅保留未平仓状态的持仓数据
lead_position_history	存储交易员已平仓的历史仓位	
lead_id（关联交易员）
open_time（开仓时间）
close_time（平仓时间）
realized_pnl（实现盈亏）	仅保留已平仓完成的仓位数据

2.2 表关联方式
三张数据表通过lead_id字段关联，可通过该字段查询单个交易员的全量数据，示例 SQL 如下：
sql
-- 将xxx替换为实际交易员的lead_id
SELECT t.*, c.symbol, c.side, h.realized_pnl 
FROM lead_trader t
LEFT JOIN lead_position_current c ON t.lead_id = c.lead_id
LEFT JOIN lead_position_history h ON t.lead_id = h.lead_id
WHERE t.lead_id = 'xxx';

代码运行过久代码运行实例如截图
