using UnityEngine;

namespace ShipyardTwin.Runtime
{
    /// <summary>
    /// 스폰된 블록 GameObject 에 붙는 얇은 뷰 핸들.
    /// 런타임 모델 참조와 Renderer 캐시만 들고 있다(로직 없음).
    /// 색상 갱신은 BlockStatusColorizer 가 이 핸들을 통해 수행한다.
    /// </summary>
    [DisallowMultipleComponent]
    public sealed class BlockView : MonoBehaviour
    {
        public BlockModel Model { get; private set; }

        private Renderer _renderer;
        private MaterialPropertyBlock _mpb;
        private static readonly int BaseColorId = Shader.PropertyToID("_BaseColor");
        private static readonly int ColorId = Shader.PropertyToID("_Color");

        public void Bind(BlockModel model, Renderer targetRenderer)
        {
            Model = model;
            _renderer = targetRenderer;
            _mpb = new MaterialPropertyBlock();
        }

        /// <summary>Renderer 만 껐다 켠다. GameObject 는 살려둬 참조와 이름 검색을 유지한다.</summary>
        public void SetVisible(bool visible)
        {
            if (_renderer != null && _renderer.enabled != visible)
            {
                _renderer.enabled = visible;
            }
        }

        /// <summary>MaterialPropertyBlock 으로 색만 바꿔 배칭을 깨지 않는다(URP Lit/Unlit 대응).</summary>
        public void SetColor(Color color)
        {
            if (_renderer == null)
            {
                return;
            }

            _renderer.GetPropertyBlock(_mpb);
            _mpb.SetColor(BaseColorId, color); // URP
            _mpb.SetColor(ColorId, color);     // Built-in 폴백
            _renderer.SetPropertyBlock(_mpb);
        }
    }
}
