from fastapi import APIRouter, HTTPException
from ..core.support_resistance.models import SRRequestPayload, SRResponse
from ..core.support_resistance.composer import SRComposer

router = APIRouter(
    prefix="/support-resistance",
    tags=["support-resistance"]
)

composer = SRComposer()

@router.post("/tdx/calculate", response_model=SRResponse)
async def calculate_tdx_sr(payload: SRRequestPayload):
    """
    计算 TDX 风格的支撑压力线。
    实际上是通用接口，根据配置融合了 Basic Rules 和 TDX 算法。
    """
    try:
        result = composer.calculate(payload)
        return result
    except Exception as e:
        # Log error in production
        print(f"Error calculating SR: {e}")
        # Return fallback or 500
        raise HTTPException(status_code=500, detail=str(e))
