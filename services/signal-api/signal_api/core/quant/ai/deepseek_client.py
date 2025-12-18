"""
AI Quant Platform - DeepSeek Client
AI-powered stock analysis using DeepSeek API.

Features:
- Candidate stock analysis
- Confidence scoring
- Market sentiment interpretation
- Smart money detection
"""

import os
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Any
import httpx

logger = logging.getLogger(__name__)


@dataclass
class AIAnalysisResult:
    """Result from DeepSeek AI analysis."""
    symbol: str
    recommendation: str  # 'strong_buy', 'buy', 'hold', 'avoid'
    confidence: float  # 0.0 - 1.0
    reasoning: str
    key_factors: List[str] = field(default_factory=list)
    risk_factors: List[str] = field(default_factory=list)
    target_price: Optional[float] = None
    stop_loss_price: Optional[float] = None
    timestamp: datetime = field(default_factory=datetime.now)
    raw_response: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol": self.symbol,
            "recommendation": self.recommendation,
            "confidence": self.confidence,
            "reasoning": self.reasoning,
            "key_factors": self.key_factors,
            "risk_factors": self.risk_factors,
            "target_price": self.target_price,
            "stop_loss_price": self.stop_loss_price,
            "timestamp": self.timestamp.isoformat()
        }


@dataclass
class DeepSeekConfig:
    """Configuration for DeepSeek API."""
    api_key: Optional[str] = None
    base_url: str = "https://api.deepseek.com/v1"
    model: str = "deepseek-chat"
    max_tokens: int = 1500
    temperature: float = 0.3  # Lower for more consistent analysis
    timeout_seconds: float = 30.0


class DeepSeekClient:
    """
    DeepSeek AI client for stock analysis.
    
    Uses DeepSeek API to analyze candidate stocks and provide:
    - Buy/Hold/Avoid recommendations
    - Confidence scores
    - Key factors and risk assessment
    
    Usage:
        client = DeepSeekClient()
        result = await client.analyze_stock(symbol, factors, market_context)
    """
    
    # System prompt for stock analysis
    SYSTEM_PROMPT = """你是一位专业的量化分析师，负责评估股票的投资潜力。

你的任务：
1. 分析给定的技术指标和市场数据
2. 识别是否存在"聪明钱"(Smart Money)进场迹象
3. 评估短期（1-3天）上涨潜力
4. 给出明确的买入建议和置信度

回复格式（JSON）：
{
    "recommendation": "strong_buy|buy|hold|avoid",
    "confidence": 0.0-1.0,
    "reasoning": "简洁的分析理由",
    "key_factors": ["看多因素1", "看多因素2"],
    "risk_factors": ["风险因素1", "风险因素2"],
    "target_price": null,
    "stop_loss_price": null
}

评判标准：
- strong_buy (置信度 0.8+): 多重信号共振，风险可控
- buy (置信度 0.6-0.8): 有积极信号，需关注风险
- hold (置信度 0.4-0.6): 信号不明确，观望为主
- avoid (置信度 < 0.4): 风险信号明显，不建议操作"""

    def __init__(self, config: Optional[DeepSeekConfig] = None):
        self.config = config or DeepSeekConfig()
        
        # Get API key from config or environment (stored privately)
        self._api_key = self.config.api_key or os.environ.get("DEEPSEEK_API_KEY")
        if not self._api_key:
            logger.warning("DeepSeek API key not set. AI analysis will be unavailable.")
        else:
            # Log that key is set, but not the key itself
            logger.info("DeepSeekClient initialized (API key configured)")
        
        self._client: Optional[httpx.AsyncClient] = None
    
    def __repr__(self) -> str:
        """Safe representation without API key."""
        return f"DeepSeekClient(model={self.config.model}, has_key={bool(self._api_key)})"
    
    async def __aenter__(self):
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit - ensures cleanup."""
        await self.close()
        return False
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client with proper lifecycle management."""
        if self._client is None or self._client.is_closed:
            # Close old client if exists but closed
            if self._client and self._client.is_closed:
                self._client = None
            
            if self._client is None:
                try:
                    self._client = httpx.AsyncClient(
                        timeout=self.config.timeout_seconds,
                        headers={
                            "Authorization": f"Bearer {self._api_key}",
                            "Content-Type": "application/json"
                        }
                    )
                except Exception as e:
                    logger.error(f"Failed to create HTTP client: {type(e).__name__}")
                    raise
        return self._client
    
    async def close(self):
        """Close HTTP client safely."""
        if self._client and not self._client.is_closed:
            try:
                await self._client.aclose()
            except Exception as e:
                logger.warning(f"Error closing HTTP client: {type(e).__name__}")
            finally:
                self._client = None
    
    def _build_analysis_prompt(
        self,
        symbol: str,
        factors: Dict[str, float],
        market_context: Optional[str] = None
    ) -> str:
        """Build the analysis prompt."""
        prompt = f"""请分析以下股票：

股票代码：{symbol}

技术指标：
"""
        for key, value in factors.items():
            if isinstance(value, float):
                prompt += f"- {key}: {value:.4f}\n"
            else:
                prompt += f"- {key}: {value}\n"
        
        if market_context:
            prompt += f"\n市场背景：\n{market_context}\n"
        
        prompt += "\n请提供你的分析建议（JSON格式）："
        
        return prompt
    
    async def analyze_stock(
        self,
        symbol: str,
        factors: Dict[str, float],
        market_context: Optional[str] = None
    ) -> AIAnalysisResult:
        """
        Analyze a stock using DeepSeek AI.
        
        Args:
            symbol: Stock symbol
            factors: Dict of technical factors
            market_context: Optional market background info
        
        Returns:
            AIAnalysisResult with recommendation and confidence
        """
        if not self._api_key:
            # Return fallback result if no API key
            return AIAnalysisResult(
                symbol=symbol,
                recommendation="hold",
                confidence=0.5,
                reasoning="AI analysis unavailable (no API key)",
                key_factors=[],
                risk_factors=["无法进行AI分析"]
            )
        
        try:
            client = await self._get_client()
            
            user_prompt = self._build_analysis_prompt(symbol, factors, market_context)
            
            response = await client.post(
                f"{self.config.base_url}/chat/completions",
                json={
                    "model": self.config.model,
                    "messages": [
                        {"role": "system", "content": self.SYSTEM_PROMPT},
                        {"role": "user", "content": user_prompt}
                    ],
                    "max_tokens": self.config.max_tokens,
                    "temperature": self.config.temperature
                }
            )
            
            response.raise_for_status()
            data = response.json()
            
            content = data["choices"][0]["message"]["content"]
            
            # Parse JSON response
            result = self._parse_response(symbol, content)
            result.raw_response = content
            
            logger.info(f"AI analysis for {symbol}: {result.recommendation} ({result.confidence:.2f})")
            
            return result
            
        except httpx.TimeoutException:
            logger.error(f"DeepSeek API timeout for {symbol}")
            return AIAnalysisResult(
                symbol=symbol,
                recommendation="hold",
                confidence=0.5,
                reasoning="API请求超时",
                risk_factors=["AI分析超时"]
            )
        except httpx.HTTPStatusError as e:
            # Log status code only, not headers (which contain API key)
            logger.error(f"DeepSeek API HTTP error for {symbol}: status={e.response.status_code}")
            return AIAnalysisResult(
                symbol=symbol,
                recommendation="hold",
                confidence=0.5,
                reasoning=f"API HTTP错误: {e.response.status_code}",
                risk_factors=["AI分析失败"]
            )
        except Exception as e:
            # Log error type only to avoid leaking sensitive info
            logger.error(f"DeepSeek API error for {symbol}: {type(e).__name__}")
            return AIAnalysisResult(
                symbol=symbol,
                recommendation="hold",
                confidence=0.5,
                reasoning=f"API错误: {type(e).__name__}",
                risk_factors=["AI分析失败"]
            )
    
    def _parse_response(self, symbol: str, content: str) -> AIAnalysisResult:
        """Parse AI response into structured result."""
        try:
            # Try to extract JSON from response
            content = content.strip()
            
            # Handle markdown code blocks
            if content.startswith("```"):
                lines = content.split("\n")
                content = "\n".join(lines[1:-1])
            
            data = json.loads(content)
            
            return AIAnalysisResult(
                symbol=symbol,
                recommendation=data.get("recommendation", "hold"),
                confidence=float(data.get("confidence", 0.5)),
                reasoning=data.get("reasoning", ""),
                key_factors=data.get("key_factors", []),
                risk_factors=data.get("risk_factors", []),
                target_price=data.get("target_price"),
                stop_loss_price=data.get("stop_loss_price")
            )
        except json.JSONDecodeError:
            # Fallback: try to extract key information
            logger.warning(f"Failed to parse JSON response for {symbol}")
            
            recommendation = "hold"
            confidence = 0.5
            
            lower_content = content.lower()
            if "strong_buy" in lower_content or "强烈买入" in content:
                recommendation = "strong_buy"
                confidence = 0.85
            elif "buy" in lower_content or "买入" in content:
                recommendation = "buy"
                confidence = 0.7
            elif "avoid" in lower_content or "规避" in content or "卖出" in content:
                recommendation = "avoid"
                confidence = 0.3
            
            return AIAnalysisResult(
                symbol=symbol,
                recommendation=recommendation,
                confidence=confidence,
                reasoning=content[:500],  # Truncate
                key_factors=[],
                risk_factors=[]
            )
    
    async def batch_analyze(
        self,
        candidates: List[Dict[str, Any]],
        market_context: Optional[str] = None,
        max_concurrent: int = 3
    ) -> List[AIAnalysisResult]:
        """
        Analyze multiple stocks concurrently.
        
        Args:
            candidates: List of {symbol, factors} dicts
            market_context: Shared market context
            max_concurrent: Max concurrent API calls
        
        Returns:
            List of AIAnalysisResult sorted by confidence
        """
        import asyncio
        
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def analyze_with_limit(candidate):
            async with semaphore:
                return await self.analyze_stock(
                    candidate["symbol"],
                    candidate.get("factors", {}),
                    market_context
                )
        
        tasks = [analyze_with_limit(c) for c in candidates]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter out exceptions
        valid_results = []
        for r in results:
            if isinstance(r, AIAnalysisResult):
                valid_results.append(r)
            elif isinstance(r, Exception):
                logger.error(f"Batch analysis error: {r}")
        
        # Sort by confidence
        valid_results.sort(key=lambda x: x.confidence, reverse=True)
        
        return valid_results
