import requests
import time
import json
import pymysql
from datetime import datetime
import urllib3
import random
from typing import Dict, List

# 忽略SSL证书警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# =========================
# 基础配置
# =========================

PROXY = {
    "http": "http://127.0.0.1:7897",
    "https": "http://127.0.0.1:7897",
}
# （修改为无代理配置（直接设为None））PROXY: Optional[Dict[str, str]] = None#去掉前面括号内容即可
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Content-Type": "application/json",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "bnc-time-zone": "Asia/Shanghai",
    "clienttype": "web",
    "origin": "https://www.binance.com",
    "referer": "https://www.binance.com/zh-CN/copy-trading",
    "sec-ch-ua": "\"Not_A Brand\";v=\"8\", \"Chromium\";v=\"120\", \"Microsoft Edge\";v=\"120\"",
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": "\"Windows\"",
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "same-origin",
    "x-ui-request-trace": "".join([chr(random.randint(97, 122)) for _ in range(36)]),
    "Connection": "keep-alive",
}

# API地址
TRADER_LIST_API = "https://www.binance.com/bapi/futures/v1/friendly/future/copy-trade/home-page/query-list"
POSITION_HISTORY_API = "https://www.binance.com/bapi/futures/v1/friendly/future/copy-trade/lead-portfolio/position-history"

# =========================
# MySQL 配置
# =========================

DB_CONFIG = dict(
    host="127.0.0.1",
    user="root",
    password="root",
    database="binance",
    charset="utf8mb4",
)


# =========================
# MySQL 工具
# =========================

def get_conn():
    try:
        conn = pymysql.connect(
            **DB_CONFIG,
            connect_timeout=10,
            read_timeout=10,
            write_timeout=10
        )
        conn.autocommit(True)
        return conn
    except pymysql.MySQLError as e:
        print(f"数据库连接失败: {e}")
        raise


def execute(sql, params=None):
    conn = None
    try:
        conn = get_conn()
        with conn.cursor() as cur:
            cur.execute(sql, params)
        conn.commit()
        return cur.rowcount
    except pymysql.MySQLError as e:
        print(f"SQL执行失败: {sql[:100]} | 错误: {e}")
        if conn:
            conn.rollback()
        return 0
    finally:
        if conn:
            conn.close()


# =========================
# 建库建表（适配字段映射）
# =========================

def init_db():
    # 创建数据库
    conn = None
    try:
        conn = pymysql.connect(
            host=DB_CONFIG["host"],
            user=DB_CONFIG["user"],
            password=DB_CONFIG["password"],
            charset="utf8mb4",
            connect_timeout=10
        )
        with conn.cursor() as cur:
            cur.execute("CREATE DATABASE IF NOT EXISTS binance DEFAULT CHARSET utf8mb4 COLLATE utf8mb4_unicode_ci")
        conn.commit()
    except pymysql.MySQLError as e:
        print(f"创建数据库失败: {e}")
        raise
    finally:
        if conn:
            conn.close()

    # 交易员表
    execute("""
    CREATE TABLE IF NOT EXISTS lead_trader (
        id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '自增主键',
        lead_id VARCHAR(64) NOT NULL UNIQUE COMMENT '交易员唯一ID',
        nickname VARCHAR(128) COMMENT '交易员昵称',
        trading_days INT COMMENT '交易天数',
        copy_count INT COMMENT '当前跟单人数',
        copy_limit INT COMMENT '跟单人数上限',
        aum DECIMAL(20,8) COMMENT '资产管理规模',
        updated_at DATETIME COMMENT '更新时间',
        raw_json JSON COMMENT '原始数据',
        INDEX idx_lead_id (lead_id) USING BTREE
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='交易员基础信息表';
    """)

    # 当前持仓表（适配字段映射）
    execute("""
    CREATE TABLE IF NOT EXISTS lead_position_current (
        id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '自增主键',
        lead_id VARCHAR(64) NOT NULL COMMENT '交易员ID',
        symbol VARCHAR(32) NOT NULL COMMENT '交易对',
        side VARCHAR(16) COMMENT '多空方向(LONG/SHORT)',
        quantity DECIMAL(20,8) COMMENT '持仓数量',
        entry_price DECIMAL(20,8) COMMENT '开仓价',
        mark_price DECIMAL(20,8) COMMENT '当前价格(markPrice)',
        unrealized_pnl DECIMAL(20,8) COMMENT '未实现盈亏',
        leverage DECIMAL(10,2) COMMENT '杠杆',
        open_time BIGINT COMMENT '开仓时间戳(毫秒)',
        collect_time DATETIME COMMENT '采集时间',
        raw_json JSON COMMENT '原始数据',
        UNIQUE KEY uniq_current (lead_id, symbol, open_time) USING BTREE,
        INDEX idx_lead_id (lead_id) USING BTREE
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='当前持仓表';
    """)

    # 历史仓位表
    execute("""
    CREATE TABLE IF NOT EXISTS lead_position_history (
        id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '自增主键',
        lead_id VARCHAR(64) NOT NULL COMMENT '交易员ID',
        symbol VARCHAR(32) NOT NULL COMMENT '交易对',
        side VARCHAR(16) COMMENT '多空方向',
        open_time BIGINT COMMENT '开仓时间戳(毫秒)',
        close_time BIGINT COMMENT '平仓时间戳(毫秒)',
        open_price DECIMAL(20,8) COMMENT '开仓价',
        close_price DECIMAL(20,8) COMMENT '平仓价',
        realized_pnl DECIMAL(20,8) COMMENT '实现盈亏',
        raw_json JSON COMMENT '原始数据',
        UNIQUE KEY uniq_history (lead_id, symbol, open_time, close_time) USING BTREE,
        INDEX idx_lead_id (lead_id) USING BTREE,
        INDEX idx_close_time (close_time) USING BTREE
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='历史仓位表';
    """)

    print("数据库和表初始化成功")


# =========================
# 请求封装
# =========================

def create_session():
    session = requests.Session()
    session.proxies.update(PROXY)
    session.trust_env = False
    session.headers.update(HEADERS)
    session.mount('https://', requests.adapters.HTTPAdapter(
        pool_connections=10,
        pool_maxsize=10,
        max_retries=3
    ))
    return session


SESSION = create_session()


def post_json(url, payload):
    try:
        r = SESSION.post(
            url,
            json=payload,
            timeout=20,
            verify=False
        )

        print(
            f"请求 {url.split('/')[-1]} | 参数: {payload.get('pageNumber', payload.get('portfolioId', 'N/A'))} | 状态码: {r.status_code}")

        if r.status_code != 200:
            print(f"非200响应: {r.text[:300]}")
            return None

        try:
            data = r.json()
        except:
            print(f"非JSON响应: {r.text[:300]}")
            return None

        if data.get("code") == 0 or data.get("success"):
            return data
        else:
            print(f"接口返回错误: {data.get('msg', '未知错误')}")
            return None

    except requests.exceptions.ProxyError:
        print("代理连接失败！请检查 127.0.0.1:7897")
        return None
    except requests.exceptions.Timeout:
        print("请求超时")
        return None
    except Exception as e:
        print(f"请求异常: {str(e)[:200]}")
        return None


# =========================
# 核心判断逻辑（完全适配你提供的规则）
# =========================

def is_current_position(position: Dict) -> bool:
    """
    判断是否为当前持仓（完全按照你提供的规则）
    :param position: 仓位数据字典
    :return: True=当前持仓，False=历史仓位
    """
    # 条件1：有平仓时间且>0 => 历史仓位
    close_time = position.get("closeTime", position.get("closed", 0))
    if close_time and close_time > 0:
        return False

    # 条件2：状态是已平仓 => 历史仓位
    status = position.get("status", "")
    if status == "All Closed":
        return False

    # 条件3：有未实现盈亏 => 当前持仓
    if position.get("unrealizedProfit") is not None:
        return True

    # 条件4：有当前价格(markPrice) => 当前持仓
    if position.get("markPrice") is not None:
        return True

    # 默认：无明确历史特征则视为当前持仓
    return True


def debug_position_data(positions: List[Dict], lead_id: str):
    """调试仓位数据，输出字段结构和统计"""
    if not positions:
        print(f"交易员{lead_id} 无仓位数据")
        return

    print(f"\n=== 交易员{lead_id} 仓位数据调试 ===")
    # 分析第一条数据结构
    sample = positions[0]
    print("第一条仓位数据关键字段:")
    print(f"  closeTime/closed: {sample.get('closeTime', sample.get('closed'))}")
    print(f"  status: {sample.get('status')}")
    print(f"  unrealizedProfit: {sample.get('unrealizedProfit')}")
    print(f"  markPrice: {sample.get('markPrice')}")
    print(f"  positionSide/side: {sample.get('positionSide', sample.get('side'))}")

    # 分类统计
    current_count = 0
    history_count = 0
    for pos in positions:
        if is_current_position(pos):
            current_count += 1
        else:
            history_count += 1

    print(f"\n统计结果:")
    print(f"  总仓位数: {len(positions)}")
    print(f"  当前持仓: {current_count} 条")
    print(f"  历史仓位: {history_count} 条")
    print("=" * 50)


# =========================
# 数据保存逻辑（适配字段映射）
# =========================

def save_to_current_table(lead_id: str, position: Dict):
    """保存到当前持仓表（完全按照字段映射）"""
    try:
        # 字段映射（严格按照你提供的规则）
        side = position.get("positionSide", position.get("side", ""))
        quantity = float(position.get("positionAmount", position.get("maxOpenInterest", 0.0)))
        entry_price = float(position.get("entryPrice", position.get("avgCost", 0.0)))
        mark_price = float(position.get("markPrice", 0.0))
        unrealized_pnl = float(position.get("unrealizedProfit", 0.0))
        leverage = float(position.get("leverage", 0.0))
        # 开仓时间：优先updateTime，其次openTime/opened
        open_time = position.get("updateTime", position.get("openTime", position.get("opened", 0)))

        # 处理负数数量（SHORT方向）
        if side == "SHORT" and quantity > 0:
            quantity = -quantity

        rowcount = execute("""
        INSERT INTO lead_position_current
        (lead_id, symbol, side, quantity, entry_price, mark_price,
         unrealized_pnl, leverage, open_time, collect_time, raw_json)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
            quantity = VALUES(quantity),
            entry_price = VALUES(entry_price),
            mark_price = VALUES(mark_price),
            unrealized_pnl = VALUES(unrealized_pnl),
            leverage = VALUES(leverage),
            collect_time = VALUES(collect_time),
            raw_json = VALUES(raw_json)
        """, (
            lead_id,
            position.get("symbol", ""),
            side,
            quantity,
            entry_price,
            mark_price,
            unrealized_pnl,
            leverage,
            open_time,
            datetime.now(),
            json.dumps(position, ensure_ascii=False)
        ))

        return rowcount > 0
    except Exception as e:
        print(f"保存当前持仓失败: {str(e)[:200]}")
        return False


def save_to_history_table(lead_id: str, position: Dict):
    """保存到历史仓位表"""
    try:
        open_time = position.get("openTime", position.get("opened", 0))
        close_time = position.get("closeTime", position.get("closed", 0))

        rowcount = execute("""
        INSERT IGNORE INTO lead_position_history
        (lead_id, symbol, side, open_time, close_time,
         open_price, close_price, realized_pnl, raw_json)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            lead_id,
            position.get("symbol", ""),
            position.get("positionSide", position.get("side", "")),
            open_time,
            close_time,
            float(position.get("entryPrice", position.get("avgCost", 0.0))),
            float(position.get("closePrice", position.get("avgClosePrice", 0.0))),
            float(position.get("realizedProfit", position.get("closingPnl", 0.0))),
            json.dumps(position, ensure_ascii=False)
        ))

        return rowcount > 0
    except Exception as e:
        print(f"保存历史仓位失败: {str(e)[:200]}")
        return False


def save_position_data(lead_id: str, position: Dict):
    """统一保存仓位数据（核心逻辑）"""
    if is_current_position(position):
        # 当前持仓
        save_to_current_table(lead_id, position)
    else:
        # 历史仓位
        save_to_history_table(lead_id, position)


# =========================
# 采集交易员列表
# =========================

def fetch_all_traders():
    all_traders = []
    page = 1
    page_size = 18
    total = 99999
    collected = 0

    print("开始采集交易员列表...")
    print("-" * 50)

    while True:
        payload = {
            "pageNumber": page,
            "pageSize": page_size,
            "timeRange": "30D",
            "dataType": "PNL",
            "favoriteOnly": False,
            "hideFull": False,
            "nickname": "",
            "order": "DESC",
            "portfolioType": "ALL",
            "useAiRecommended": False,
            "userAsset": 0
        }

        data = post_json(TRADER_LIST_API, payload)
        if not data:
            print(f"第{page}页采集失败，重试一次...")
            time.sleep(2)
            data = post_json(TRADER_LIST_API, payload)
            if not data:
                print(f"第{page}页重试失败，终止采集")
                break

        response_data = data.get("data", {})
        traders = response_data.get("list", response_data.get("items", []))

        if not traders:
            print(f"第{page}页无数据，采集结束")
            break

        all_traders.extend(traders)
        collected += len(traders)
        total = response_data.get("total", total)

        print(f"第{page}页采集成功 | 本页{len(traders)}条 | 累计{collected}条 | 总条数{total}")

        has_more = response_data.get("hasMore", True)
        if (collected >= total) or (len(traders) < page_size) or (not has_more):
            print(f"已采集全部交易员！总计{collected}条")
            break

        page += 1
        delay = 1.5 + random.random()
        print(f"等待{delay:.1f}秒后采集第{page}页...")
        time.sleep(delay)

    print("-" * 50)
    return all_traders


# =========================
# 采集仓位数据
# =========================

def fetch_and_save_all_positions(lead_id: str):
    """采集并保存单个交易员的所有仓位数据"""
    page = 1
    all_positions = []

    while True:
        payload = {
            "portfolioId": lead_id,
            "pageNumber": page,
            "pageSize": 100,
            "sort": "OPENING",
            "timeRange": "30D"
        }

        data = post_json(POSITION_HISTORY_API, payload)
        if not data:
            break

        position_data = data.get("data", {})
        positions = position_data.get("list", [])

        if not positions:
            break

        all_positions.extend(positions)
        print(f"交易员{lead_id} | 仓位第{page}页 | {len(positions)}条")

        # 分页判断
        total = position_data.get("total", 0)
        if page * 100 >= total or len(positions) < 100:
            break

        page += 1
        time.sleep(0.8)

    # 调试数据结构
    debug_position_data(all_positions, lead_id)

    # 批量保存
    current_count = 0
    history_count = 0
    for pos in all_positions:
        if is_current_position(pos):
            current_count += 1
        else:
            history_count += 1
        save_position_data(lead_id, pos)

    print(f"交易员{lead_id} | 保存完成 | 当前持仓{current_count}条 | 历史仓位{history_count}条")
    return current_count + history_count


# =========================
# 保存交易员数据
# =========================

def save_trader(t):
    lead_id = t.get("leadPortfolioId", t.get("portfolioId", ""))
    if not lead_id:
        return False

    try:
        rowcount = execute("""
        INSERT INTO lead_trader
        (lead_id, nickname, trading_days, copy_count, copy_limit, aum, updated_at, raw_json)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
        ON DUPLICATE KEY UPDATE
            nickname=VALUES(nickname),
            trading_days=VALUES(trading_days),
            copy_count=VALUES(copy_count),
            copy_limit=VALUES(copy_limit),
            aum=VALUES(aum),
            updated_at=VALUES(updated_at),
            raw_json=VALUES(raw_json)
        """, (
            lead_id,
            t.get("nickName", t.get("nickname", "")),
            t.get("tradingDays", 0),
            t.get("copyNumber", t.get("followerCount", 0)),
            t.get("copyNumberMax", t.get("followerLimit", 0)),
            t.get("aum", 0.0),
            datetime.now(),
            json.dumps(t, ensure_ascii=False)
        ))

        return rowcount > 0
    except Exception as e:
        print(f"保存交易员{lead_id}失败: {str(e)[:200]}")
        return False


# =========================
# 主入口
# =========================

def main():
    try:
        print(f"[{datetime.now()}] 币安跟单数据采集程序启动（适配官方判断规则）")
        print("=" * 60)

        # 1. 初始化数据库
        init_db()

        # 2. 采集所有交易员
        traders = fetch_all_traders()
        if not traders:
            print("未采集到任何交易员数据！")
            return

        # 3. 逐个采集仓位数据
        print("\n开始采集仓位数据...")
        print("=" * 60)
        success_traders = 0
        total_positions = 0

        for i, t in enumerate(traders, 1):
            lead_id = t.get("leadPortfolioId", t.get("portfolioId", ""))
            if not lead_id:
                print(f"[{i}/{len(traders)}] 跳过无ID交易员")
                continue

            print(f"\n[{i}/{len(traders)}] 处理交易员 {lead_id}")

            # 保存交易员
            if save_trader(t):
                # 采集并保存所有仓位（自动区分当前/历史）
                pos_count = fetch_and_save_all_positions(lead_id)
                total_positions += pos_count
                success_traders += 1
            else:
                print(f"交易员 {lead_id} 保存失败")

            # 控制频率
            time.sleep(1.2)

        print("=" * 60)
        print(f"[{datetime.now()}] 采集完成！")
        print(f"成功处理交易员: {success_traders}/{len(traders)}")
        print(f"总计保存仓位数据: {total_positions}条")

        # 数据库验证
        current_count = execute("SELECT COUNT(*) FROM lead_position_current")[0]
        history_count = execute("SELECT COUNT(*) FROM lead_position_history")[0]
        print(f"数据库验证: 当前持仓{current_count}条 | 历史仓位{history_count}条")

    except KeyboardInterrupt:
        print(f"\n[{datetime.now()}] 程序被手动终止")
    except Exception as e:
        print(f"\n[{datetime.now()}] 程序出错: {str(e)}")
        raise


if __name__ == "__main__":
    main()