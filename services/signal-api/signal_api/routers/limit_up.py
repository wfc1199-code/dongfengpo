"""
涨停板 / 连板追踪 API
使用 AkShare stock_zt_pool_em API 获取准确的连板数据
集成统一5维评分系统
"""
from fastapi import APIRouter
import asyncio
import logging
from typing import Dict, Any
from datetime import datetime, timedelta

# 导入统一评分器
from ..core.quant.scorer import get_scorer, StockMetrics

router = APIRouter(
    prefix="/api/limit-up",
    tags=["limit-up"],
    responses={404: {"description": "Not found"}},
)

logger = logging.getLogger(__name__)


@router.get("/predictions")
async def get_limit_up_predictions(limit: int = 50):
    """
    获取涨停池数据（包含准确的连板数）
    
    使用 AkShare 的 stock_zt_pool_em API，与原始后端一致
    返回包含 consecutive_days 的股票列表
    """
    try:
        import akshare as ak
        
        logger.info("🔍 获取涨停池数据（AkShare API）...")
        
        loop = asyncio.get_event_loop()
        df = None
        data_date = None
        
        # 尝试获取涨停数据：先尝试今天，如果为空则尝试前几个交易日
        for days_ago in range(5):
            try_date = datetime.now() - timedelta(days=days_ago)
            date_str = try_date.strftime("%Y%m%d")
            
            # 跳过周末
            if try_date.weekday() >= 5:
                continue
            
            try:
                df = await loop.run_in_executor(
                    None,
                    ak.stock_zt_pool_em,
                    date_str
                )
                
                if df is not None and not df.empty:
                    data_date = date_str
                    if days_ago == 0:
                        logger.info(f"✅ 获取到 {len(df)} 只涨停股票 - 今日数据")
                    else:
                        logger.info(f"✅ 获取到 {len(df)} 只涨停股票 - {date_str}数据")
                    break
                else:
                    logger.debug(f"{date_str} 无涨停数据，尝试前一天")
                    
            except Exception as e:
                logger.debug(f"获取 {date_str} 涨停数据失败: {e}")
                continue
        
        if df is None or df.empty:
            logger.warning("涨停池数据为空（包括历史数据），返回空列表")
            return {
                "code": 200,
                "message": "暂无涨停数据",
                "data": {"stocks": []},
                "date": None
            }
        
        # 转换为标准格式
        stocks = []
        for _, row in df.head(limit * 2).iterrows():  # 取更多以便排序后筛选
            try:
                code = str(row.get('代码', ''))
                name = str(row.get('名称', ''))
                price = float(row.get('最新价', 0) or 0)
                change_percent = float(row.get('涨跌幅', 0) or 0)
                volume = int(row.get('成交量', 0) or 0)
                amount = float(row.get('成交额', 0) or 0)
                turnover_rate = float(row.get('换手率', 0) or 0)
                consecutive_days = int(row.get('连板数', 1) or 1)  # AkShare 直接返回连板数
                industry = str(row.get('所属行业', '其他') or '其他')
                
                # 封板时间
                first_limit_time = str(row.get('首次封板时间', '') or '')
                last_limit_time = str(row.get('最后封板时间', '') or '')
                
                stocks.append({
                    "symbol": code,
                    "code": code,  # 兼容前端
                    "name": name,
                    "price": price,
                    "change_percent": change_percent,
                    "consecutive_days": consecutive_days,
                    "industry": industry,
                    "volume": volume,
                    "amount": amount,
                    "turnover_rate": turnover_rate,
                    "first_limit_up_time": first_limit_time,
                    "last_limit_up_time": last_limit_time,
                    "reason": f"{consecutive_days}连板" if consecutive_days > 1 else "首板涨停",
                    "data_source": "akshare_limit_up_pool"
                })
            except Exception as e:
                logger.warning(f"转换涨停股票数据失败: {e}")
                continue
        
        # 按连板数排序（高到低）
        stocks.sort(key=lambda x: x['consecutive_days'], reverse=True)
        stocks = stocks[:limit]
        
        logger.info(f"✅ 返回 {len(stocks)} 只涨停股票（包含准确连板数）")
        
        # 统计连板分布
        board_stats = {}
        for s in stocks:
            days = s['consecutive_days']
            board_stats[days] = board_stats.get(days, 0) + 1
        logger.info(f"📊 连板分布: {board_stats}")
        
        return {
            "code": 200,
            "message": "success",
            "data": {"stocks": stocks},
            "date": data_date
        }
        
    except ImportError:
        logger.error("akshare 未安装，使用回退方案")
        return await get_fallback_limit_up(limit)
    except Exception as e:
        logger.error(f"获取涨停池数据失败: {e}")
        return await get_fallback_limit_up(limit)


async def get_fallback_limit_up(limit: int) -> Dict[str, Any]:
    """
    回退方案：使用东方财富简单接口获取涨停股票
    注意：此方法无法获取准确的连板数
    """
    import aiohttp
    
    logger.warning("⚠️ 使用回退方案获取涨停数据（无连板数）")
    
    url = 'http://push2.eastmoney.com/api/qt/clist/get'
    params = {
        'pn': '1', 'pz': '100', 'po': '1', 'np': '1',
        'ut': 'bd1d9ddb04089700cf9c27f6f7426281',
        'fltt': '2', 'invt': '2', 'fid': 'f3',
        'fs': 'm:0+t:6,m:0+t:13,m:0+t:80,m:1+t:2,m:1+t:23',
        'fields': 'f1,f2,f3,f4,f5,f6,f12,f14'
    }
    
    timeout = aiohttp.ClientTimeout(total=5)
    try:
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(url, params=params) as response:
                stocks = []
                if response.status == 200:
                    data = await response.json()
                    if 'data' in data and 'diff' in data['data']:
                        for s in data['data']['diff']:
                            change_pct = float(s.get('f3', 0) or 0)
                            if change_pct > 9.0:  # 涨幅大于9%视为涨停
                                stocks.append({
                                    "symbol": s.get('f12'),
                                    "code": s.get('f12'),
                                    "name": s.get('f14'),
                                    "price": s.get('f2'),
                                    "change_percent": change_pct,
                                    "consecutive_days": 1,  # 回退方案无法获取真实连板数
                                    "reason": "涨停（连板数未知）",
                                    "data_source": "eastmoney_fallback"
                                })
                return {
                    "code": 200, 
                    "message": "success (fallback)", 
                    "data": {"stocks": stocks[:limit]},
                    "date": None
                }
    except Exception as e:
        logger.error(f"回退方案也失败: {e}")
        return {"code": 200, "message": "error", "data": {"stocks": []}}


# =============================================================================
# 内部帮助函数：获取涨停池DataFrame（带缓存）
# =============================================================================
_zt_pool_cache = {"df": None, "date": None, "timestamp": None}

async def _get_zt_pool_df():
    """获取涨停池DataFrame（带内存缓存）"""
    import akshare as ak
    
    # 简单的内存缓存（60秒有效）
    now = datetime.now()
    if (_zt_pool_cache["df"] is not None and 
        _zt_pool_cache["timestamp"] and 
        (now - _zt_pool_cache["timestamp"]).seconds < 60):
        return _zt_pool_cache["df"], _zt_pool_cache["date"]
    
    loop = asyncio.get_event_loop()
    
    for days_ago in range(5):
        try_date = now - timedelta(days=days_ago)
        if try_date.weekday() >= 5:
            continue
        
        date_str = try_date.strftime("%Y%m%d")
        try:
            df = await loop.run_in_executor(None, ak.stock_zt_pool_em, date_str)
            if df is not None and not df.empty:
                _zt_pool_cache["df"] = df
                _zt_pool_cache["date"] = date_str
                _zt_pool_cache["timestamp"] = now
                logger.info(f"✅ 缓存涨停池数据: {len(df)}只, 日期: {date_str}")
                return df, date_str
        except Exception as e:
            logger.debug(f"获取 {date_str} 涨停数据失败: {e}")
            continue
    
    return None, None


# =============================================================================
# 二板候选接口
# =============================================================================
@router.get("/second-board-candidates")
async def get_second_board_candidates(limit: int = 20):
    """
    获取二板候选股票
    
    从首板股票中筛选明日可能涨停的候选：
    - 筛选连板数=1的首板股票
    - 排除一字板
    - 排除弱势股（炸板过多、换手率低、成交额低）
    - 计算晋级概率
    """
    try:
        df, data_date = await _get_zt_pool_df()
        
        if df is None or df.empty:
            return {
                "code": 200,
                "message": "暂无涨停数据",
                "data": {"candidates": [], "total_count": 0, "update_time": datetime.now().isoformat()}
            }
        
        # 筛选首板股票（连板数 == 1）
        if '连板数' in df.columns:
            first_board_df = df[df['连板数'] == 1].copy()
            logger.info(f"✅ 筛选出 {len(first_board_df)} 只首板股票（共 {len(df)} 只涨停）")
        else:
            first_board_df = df.head(30).copy()
            logger.warning("⚠️ 数据中没有'连板数'字段，返回前30只")
        
        # 排除一字板
        if '炸板次数' in first_board_df.columns and '首次封板时间' in first_board_df.columns:
            before_filter = len(first_board_df)
            
            def is_yi_zi_ban(row):
                seal_time = str(row.get('首次封板时间', ''))
                burst_count = int(row.get('炸板次数', 0) or 0)
                if seal_time and len(seal_time) >= 4:
                    if seal_time[:4] <= '0925' and burst_count == 0:
                        return True
                return False
            
            first_board_df = first_board_df[~first_board_df.apply(is_yi_zi_ban, axis=1)]
            logger.info(f"✅ 排除一字板后剩余 {len(first_board_df)} 只（过滤 {before_filter - len(first_board_df)} 只）")
        
        candidates = []
        
        for _, row in first_board_df.iterrows():
            code = str(row.get('代码', ''))
            name = str(row.get('名称', ''))
            change_percent = float(row.get('涨跌幅', 0) or 0)
            current_price = float(row.get('最新价', 0) or 0)
            turnover_rate = float(row.get('换手率', 0) or 0)
            amount = float(row.get('成交额', 0) or 0)
            seal_time = str(row.get('首次封板时间', '09:30') or '09:30')
            burst_count = int(row.get('炸板次数', 0) or 0)
            industry = str(row.get('所属行业', '未知') or '未知')
            volume_ratio = float(row.get('量比', 1.0) or 1.0)
            
            # 过滤弱势股
            if burst_count > 3:
                continue
            if turnover_rate < 5:
                continue
            if amount < 100000000:  # 成交额 < 1亿
                continue
            
            # 使用明日潜力适配器进行评估 (Ambush策略)
            try:
                # 延迟导入以避免循环依赖
                from ..core.quant.adapters import TomorrowCandidateAdapter
                
                adapter = TomorrowCandidateAdapter()
                
                # 构造适配器需要的输入数据
                candidate_data = {
                    'code': code,
                    'name': name,
                    'current_price': current_price,
                    'change_percent': change_percent,
                    'turnover_rate': turnover_rate,
                    'amount': amount,
                    'volume_ratio': volume_ratio,
                    'industry': industry,
                    'limit_up_time': seal_time,
                    'burst_count': burst_count
                }
                
                # 调用适配器 (内部会执行: 5维评分 -> 历史数据获取 -> Ambush策略评估)
                # 注意: 如果历史数据不足，这里会返回 None (强制要求真实数据)
                result = await adapter.adapt_tomorrow_candidate(candidate_data)
                
                if result is None:
                    logger.debug(f"Ambush跳过 {code}: 数据不足或不符合条件")
                    continue
                
                # 解包结果
                (
                    probability,
                    unified_score,
                    strength_level,
                    risk_level,
                    reasons,
                    risks,
                    ambush_score,
                    ambush_factors
                ) = (
                    result['probability'],
                    result['unifiedScore'],
                    result['strengthLevel'],
                    result['riskLevel'],
                    result['reasons'],
                    result['risks'],
                    result.get('ambushScore', 0),
                    result.get('ambushFactors', {})
                )
                
                # 构造返回对象
                candidates.append({
                    'code': code,
                    'name': name,
                    'firstBoardTime': seal_time,
                    'sealAmount': round(amount / 1e8, 2),
                    'probability': probability,
                    'unifiedScore': unified_score,
                    'strengthLevel': strength_level,
                    'riskLevel': risk_level,
                    'ambushScore': ambush_score,      # 新增: 潜伏评分
                    'ambushFactors': ambush_factors,  # 新增: 潜伏因子
                    'scoreBreakdown': result.get('scoreBreakdown', {}),
                    'reason': f'首板潜伏；Ambush评分{ambush_score:.0f}；{ambush_factors.get("trend_intensity", "评级")}',
                    'reasons': reasons,
                    'risks': risks,
                    'theme': industry,
                    'technicalScore': int(ambush_factors.get('score_vol', 60)),
                    'marketScore': int(ambush_factors.get('score_trend', 60)),
                    'fundScore': int(ambush_factors.get('score_basic', 60)),
                    'currentPrice': current_price,
                    'changePercent': change_percent,
                    'turnoverRate': turnover_rate,
                    'burstCount': burst_count
                })
                
            except Exception as e:
                logger.error(f"Ambush评估失败 {code}: {e}")
                continue
            
            if len(candidates) >= limit:
                break
        
        # 按Ambush分数和概率排序
        candidates.sort(key=lambda x: (x.get('ambushScore', 0), x['probability']), reverse=True)
        
        logger.info(f"✅ 返回 {len(candidates)} 只Ambush优选股")
        
        return {
            "code": 200,
            "message": "success",
            "data": {
                "candidates": candidates,
                "total_count": len(candidates),
                "update_time": datetime.now().isoformat(),
                "date": data_date
            }
        }
        
    except ImportError:
        logger.error("akshare 未安装")
        return {"code": 500, "message": "akshare未安装", "data": {"candidates": []}}
    except Exception as e:
        logger.error(f"获取二板候选失败: {e}")
        return {"code": 500, "message": str(e), "data": {"candidates": []}}


# =============================================================================
# 实时预测接口（盯盘雷达用）
# =============================================================================
@router.get("/realtime-predictions")
async def get_realtime_predictions(limit: int = 50):
    """
    实时涨停预测（盯盘雷达）
    
    返回分时段的涨停预测数据，用于盯盘雷达组件
    """
    try:
        df, data_date = await _get_zt_pool_df()
        
        if df is None or df.empty:
            return {
                "code": 200,
                "message": "暂无涨停数据",
                "data": {
                    "segments": [],
                    "statistics": {"total_stocks": 0},
                    "update_time": datetime.now().isoformat()
                }
            }
        
        # 时间段定义 - ID与前端activeTab匹配
        time_segments = [
            {"id": "auction", "name": "🚀 开盘冲刺", "period": "09:30-10:00", "description": "开盘30分钟内涨停"},
            {"id": "anomaly", "name": "📈 早盘主升", "period": "10:00-11:00", "description": "早盘主升阶段"},
            {"id": "breakthrough", "name": "🔄 午盘发力", "period": "11:00-13:30", "description": "午盘前后"},
            {"id": "late", "name": "⚡ 尾盘突袭", "period": "13:30-15:00", "description": "尾盘拉升"}
        ]

        
        # 按封板时间分类
        segmented_stocks = {i: [] for i in range(len(time_segments))}
        
        for _, row in df.head(100).iterrows():
            code = str(row.get('代码', ''))
            name = str(row.get('名称', ''))
            change_percent = float(row.get('涨跌幅', 0) or 0)
            price = float(row.get('最新价', 0) or 0)
            turnover_rate = float(row.get('换手率', 0) or 0)
            amount = float(row.get('成交额', 0) or 0)
            seal_time = str(row.get('首次封板时间', '') or '')
            consecutive_days = int(row.get('连板数', 1) or 1)
            volume_ratio = float(row.get('量比', 1.0) or 1.0)
            
            # 使用统一5维评分系统
            try:
                scorer = get_scorer()
                metrics = StockMetrics(
                    code=code,
                    name=name,
                    price=price,
                    change_pct=change_percent,
                    turnover_rate=turnover_rate,
                    amount=amount,
                    volume_ratio=volume_ratio,
                )
                result = scorer.score(metrics)
                score = result.total_score
                level = result.strength_level.value
                risk = result.risk_level.value
                reasons = result.reasons
            except Exception as e:
                logger.warning(f"评分失败 {code}: {e}")
                # 回退到简化评分
                score = min(100, change_percent * 8 + turnover_rate * 2 + min(amount / 1e7, 10) * 5)
                level = "极高" if score >= 85 else "高" if score >= 75 else "中高" if score >= 65 else "中"
                risk = "高风险" if change_percent >= 7 else "中等"
                reasons = [f"涨幅{change_percent:.2f}%"]
            
            stock_data = {
                "code": code,
                "name": name,
                "price": price,
                "changePercent": change_percent,
                "turnoverRate": turnover_rate,
                "amount": amount,
                "volumeRatio": volume_ratio,
                "predictionScore": round(score, 1),
                "predictionLevel": level,
                "riskLevel": risk,
                # 新增: 5维评分详情
                "scoreBreakdown": {
                    "changeScore": result.change_score if 'result' in locals() else 0,
                    "turnoverScore": result.turnover_score if 'result' in locals() else 0,
                    "volumeScore": result.volume_score if 'result' in locals() else 0,
                    "shapeScore": result.shape_score if 'result' in locals() else 0,
                    "comboScore": result.combo_score if 'result' in locals() else 0,
                },
                "sealTime": seal_time,
                "consecutive_days": consecutive_days,
                "predictionReasons": reasons + ([f"{consecutive_days}连板"] if consecutive_days > 1 else ["首板"])
            }
            
            # 根据封板时间分类
            segment_id = 0
            if seal_time and len(seal_time) >= 4:
                hhmm = seal_time[:4].replace(':', '')
                if hhmm <= '1000':
                    segment_id = 0
                elif hhmm <= '1100':
                    segment_id = 1
                elif hhmm <= '1330':
                    segment_id = 2
                else:
                    segment_id = 3
            
            segmented_stocks[segment_id].append(stock_data)
        
        # 构建返回数据
        result_segments = []
        total_stocks = 0
        
        for i, segment_info in enumerate(time_segments):
            stocks = segmented_stocks[i][:limit]
            stocks.sort(key=lambda x: x['predictionScore'], reverse=True)
            total_stocks += len(stocks)
            
            # 前端期望的格式: {id, name, description, stocks, count}
            result_segments.append({
                "id": str(segment_info["id"]),  # 前端用字符串ID匹配tab
                "name": segment_info["name"],
                "description": segment_info["description"],
                "stocks": stocks,
                "count": len(stocks)
            })

        
        return {
            "code": 200,
            "message": "success",
            "data": {
                "segments": result_segments,
                "statistics": {
                    "total_stocks": total_stocks,
                    "segments_count": len(time_segments)
                },
                "update_time": datetime.now().isoformat(),
                "date": data_date
            }
        }
        
    except ImportError:
        logger.error("akshare 未安装")
        return {"code": 500, "message": "akshare未安装", "data": {"segments": []}}
    except Exception as e:
        logger.error(f"获取实时预测失败: {e}")
        return {"code": 500, "message": str(e), "data": {"segments": []}}


@router.get("/anomaly-radar")
async def get_anomaly_radar(limit: int = 50):
    """
    盘中异动雷达 - 全市场扫描
    
    扫描全市场股票，检测价格/量比/换手异动，
    返回涨停前的潜力股票（而非已涨停股票）
    
    异动条件:
    - 涨幅 >= 5% (接近涨停)
    - 量比 >= 3 (成交放大)
    - 换手率 >= 3% (活跃交易)
    """
    try:
        from ..core.quant.anomaly_scanner import get_scanner
        
        logger.info("🔍 执行全市场异动扫描...")
        
        scanner = get_scanner()
        
        # 检查是否交易时间
        if not scanner.is_trading_time():
            return {
                "code": 200,
                "message": "非交易时间",
                "data": {
                    "candidates": [],
                    "is_trading_time": False,
                    "update_time": datetime.now().isoformat()
                }
            }
        
        # 执行扫描
        candidates = await scanner.scan()
        
        # 转换为响应格式
        result_candidates = []
        for candidate in candidates[:limit]:
            result_candidates.append({
                "code": candidate.code,
                "name": candidate.name,
                "price": candidate.price,
                "changePct": candidate.change_pct,
                "volumeRatio": candidate.volume_ratio,
                "turnoverRate": candidate.turnover_rate,
                "amount": candidate.amount,
                "speed1m": candidate.speed_1m,
                "speed3m": candidate.speed_3m,
                "anomalyScore": candidate.anomaly_score,
                "anomalyTypes": [t.value for t in candidate.anomaly_types],
                "detectedAt": candidate.detected_at.isoformat(),
            })
        
        logger.info(f"✅ 异动扫描完成: {len(result_candidates)} 只候选")
        
        return {
            "code": 200,
            "message": "success",
            "data": {
                "candidates": result_candidates,
                "is_trading_time": True,
                "total_scanned": len(candidates),
                "update_time": datetime.now().isoformat()
            }
        }
        
    except Exception as e:
        logger.error(f"异动扫描失败: {e}")
        import traceback
        traceback.print_exc()
        return {"code": 500, "message": str(e), "data": {"candidates": []}}


@router.get("/engine-status")
async def get_engine_status():
    """
    获取实时引擎状态
    """
    try:
        from ..core.quant.realtime_engine import get_engine
        
        engine = get_engine()
        return {
            "code": 200,
            "message": "success",
            "data": engine.get_stats()
        }
    except Exception as e:
        return {"code": 500, "message": str(e), "data": {}}


@router.post("/start-radar")
async def start_radar_engine():
    """
    启动异动雷达实时引擎
    
    启动后每3秒自动扫描一次全市场，发现异动股票后推送
    """
    try:
        from ..core.quant.realtime_engine import get_engine
        from .quant import get_engine_state, broadcast_signal
        
        engine = get_engine(broadcast_callback=broadcast_signal)
        await engine.start()
        
        return {
            "code": 200,
            "message": "实时雷达已启动",
            "data": engine.get_stats()
        }
    except Exception as e:
        logger.error(f"启动实时雷达失败: {e}")
        return {"code": 500, "message": str(e), "data": {}}


@router.post("/stop-radar")
async def stop_radar_engine():
    """
    停止异动雷达实时引擎
    """
    try:
        from ..core.quant.realtime_engine import stop_engine
        
        await stop_engine()
        
        return {
            "code": 200,
            "message": "实时雷达已停止",
            "data": {}
        }
    except Exception as e:
        logger.error(f"停止实时雷达失败: {e}")
        return {"code": 500, "message": str(e), "data": {}}

