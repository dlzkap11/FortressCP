using Unity.Collections;
using UnityEngine;
using UnityEngine.InputSystem;

public class SpikeTest : MonoBehaviour
{

    private Vector2 clickPos;
    [Range(0, 2f)]
    [SerializeField] private float radius;


    [SerializeField] private GameObject map;
    [SerializeField] Texture2D origin;
    [SerializeField] Texture2D copy;
    SpriteRenderer mapSr;
    Sprite copyMapSprite;
    const int PPU = 24;
    void Start()
    {
        copy = new Texture2D(origin.width, origin.height, TextureFormat.RGBA32, false);
        copy.filterMode = FilterMode.Point;
        copy.wrapMode = TextureWrapMode.Clamp;

        NativeArray<Color32> originalData = origin.GetPixelData<Color32>(0);
        copy.SetPixelData(originalData, 0);
        copy.Apply();

        /*
        copy.SetPixels32(origin.GetPixels32());
        Color32[] colors = copy.GetPixels32();
        copy.SetPixels32(colors);
        copy.Apply();
        */

        Rect rect = new Rect(0, 0, origin.width, origin.height);
        mapSr = map.GetComponent<SpriteRenderer>();
        copyMapSprite = Sprite.Create(copy, rect, Vector2.zero, PPU);
        mapSr.sprite = copyMapSprite;
    }


    void Update()
    {
        if (Mouse.current.leftButton.wasPressedThisFrame)
        {
            clickPos = Camera.main.ScreenToWorldPoint(Mouse.current.position.ReadValue());
            clickPos = map.transform.InverseTransformPoint(clickPos);

            TerrainDestroy(clickPos, radius);
            Debug.Log($"{clickPos.x}, {clickPos.y}");
        }
    }

    public void TerrainDestroy(Vector2 pos, float r)
    {



        //  * [준비]
        //  중심x, 중심y ← 로컬 좌표 × PPU            (실수 그대로)
        //  픽셀반경     ← 반경 × PPU
        //  반경제곱     ← 픽셀반경 × 픽셀반경
        float x = pos.x * PPU;
        float y = pos.y * PPU;
        float pixelR = r * PPU;
        float powR = pixelR * pixelR;

        int width = copy.width;
        int height = copy.height;
        //  [감싸는 사각형]
        //  시작x ← 내림(중심x − 픽셀반경)  → 0 ~ 가로−1 사이로 자르기
        //  끝x   ← 올림(중심x + 픽셀반경)  → 0 ~ 가로−1 사이로 자르기
        //  시작y, 끝y 도 같은 방식
        int startX = Mathf.FloorToInt(x - pixelR);
        startX = Mathf.Clamp(startX, 0, width - 1);
        int lastX = Mathf.CeilToInt(x + pixelR);
        lastX = Mathf.Clamp(lastX, 0, width - 1);

        int startY = Mathf.FloorToInt(y - pixelR);
        startY = Mathf.Clamp(startY, 0, height - 1);
        int lastY = Mathf.CeilToInt(y + pixelR);
        lastY = Mathf.Clamp(lastY, 0, height - 1);

        //  [픽셀 데이터]
        //  픽셀배열 ← 복사본 텍스처의 픽셀 데이터 (GetPixelData)
        NativeArray<Color32> copyData = copy.GetPixelData<Color32>(0);

        //  [훑기]
        //  py 를 시작y 부터 끝y 까지 (끝 포함) 반복:
        //      px 를 시작x 부터 끝x 까지 (끝 포함) 반복:
        //          dx ← (px + 0.5) − 중심x
        //          dy ← (py + 0.5) − 중심y
        //          만약 dx² + dy² ≤ 반경제곱 이면:
        //              칸번호 ← py × 가로 + px
        //              그 칸의 픽셀을 꺼내서 → 알파를 0으로 → 다시 넣기
        for (int py = startY; py <= lastY; py++)
            for (int px = startX; px <= lastX; px++)
            {
                float dx = (px + 0.5f) - x;
                float dy = (py + 0.5f) - y;
                if (dx * dx + dy * dy <= powR)
                {
                    int num = py * width + px;
                    Color32 temp = copyData[num];
                    temp.a = 0;
                    copyData[num] = temp;
                }
            }

        //  [마무리]
        //  복사본 텍스처 Apply   (반복문 바깥에서 한 번)
        copy.Apply();

    }

    private void OnDrawGizmos()
    {
        Gizmos.color = Color.red;
        Gizmos.DrawWireSphere(clickPos, radius);
    }
}
