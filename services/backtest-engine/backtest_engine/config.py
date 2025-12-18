"""
配置管理
"""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """应用配置"""

    # 服务配置
    SERVICE_NAME: str = "backtest-engine"
    SERVICE_PORT: int = 9003
    DEBUG: bool = False

    # 数据库配置（可选，后续添加）
    # DATABASE_URL: str = "postgresql://..."

    # Redis配置（可选，用于任务队列）
    # REDIS_URL: str = "redis://localhost:6379"

    # 回测配置
    DEFAULT_INITIAL_CASH: float = 100000.0
    DEFAULT_COMMISSION: float = 0.0003  # 0.03%
    DEFAULT_SLIPPAGE: float = 0.001  # 0.1%

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
