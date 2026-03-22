-- 创建数据库（若不存在）
CREATE DATABASE IF NOT EXISTS binance DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE binance;

-- 交易员表
DROP TABLE IF EXISTS lead_trader;
CREATE TABLE lead_trader (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '自增主键',
    lead_id VARCHAR(64) NOT NULL COMMENT '交易员唯一ID',
    nickname VARCHAR(128) COMMENT '交易员昵称',
    trading_days INT COMMENT '交易天数',
    copy_count INT COMMENT '当前跟单人数',
    copy_limit INT COMMENT '跟单人数上限',
    aum DECIMAL(20,8) COMMENT '资产管理规模',
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '数据更新时间',
    raw_json JSON COMMENT '接口返回原始数据',
    PRIMARY KEY (id),
    UNIQUE KEY uk_lead_id (lead_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='币安跟单交易员基础信息表';

-- 当前持仓表
DROP TABLE IF EXISTS lead_position_current;
CREATE TABLE lead_position_current (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '自增主键',
    lead_id VARCHAR(64) NOT NULL COMMENT '交易员ID',
    symbol VARCHAR(32) COMMENT '交易对',
    side VARCHAR(16) COMMENT '多空方向(LONG/SHORT)',
    quantity DECIMAL(20,8) COMMENT '持仓数量(SHORT为负数)',
    entry_price DECIMAL(20,8) COMMENT '开仓价',
    mark_price DECIMAL(20,8) COMMENT '当前标记价格',
    unrealized_pnl DECIMAL(20,8) COMMENT '未实现盈亏',
    leverage DECIMAL(10,2) COMMENT '杠杆倍数',
    open_time BIGINT COMMENT '开仓时间戳(毫秒)',
    collect_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '数据采集时间',
    raw_json JSON COMMENT '接口返回原始数据',
    PRIMARY KEY (id),
    UNIQUE KEY uk_lead_symbol_open (lead_id, symbol, open_time)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='币安跟单交易员当前持仓表';

-- 历史仓位表
DROP TABLE IF EXISTS lead_position_history;
CREATE TABLE lead_position_history (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '自增主键',
    lead_id VARCHAR(64) NOT NULL COMMENT '交易员ID',
    symbol VARCHAR(32) COMMENT '交易对',
    side VARCHAR(16) COMMENT '多空方向',
    open_time BIGINT COMMENT '开仓时间戳(毫秒)',
    close_time BIGINT COMMENT '平仓时间戳(毫秒)',
    open_price DECIMAL(20,8) COMMENT '开仓价',
    close_price DECIMAL(20,8) COMMENT '平仓价',
    realized_pnl DECIMAL(20,8) COMMENT '实现盈亏',
    raw_json JSON COMMENT '接口返回原始数据',
    PRIMARY KEY (id),
    UNIQUE KEY uk_lead_symbol_open_close (lead_id, symbol, open_time, close_time)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='币安跟单交易员历史仓位表';