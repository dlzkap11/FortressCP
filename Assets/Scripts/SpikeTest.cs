using UnityEditor;
using UnityEngine;
using UnityEngine.InputSystem;

public class SpikeTest : MonoBehaviour
{

    private Vector2 clickPos;
    [SerializeField] private GameObject map;
    [Range(0, 2f)]
    [SerializeField] private float radius;
    [SerializeField] Texture2D origin;
    Texture2D copy;
    void Start()
    {
        copy = origin;
    }

    
    void Update()
    {
        if (Input.GetMouseButtonDown(0))
        {
            clickPos = Camera.main.ScreenToWorldPoint(Mouse.current.position.ReadValue());
            clickPos = map.transform.InverseTransformPoint(clickPos);


            
            TerrianDestroy(clickPos, radius);
            Debug.Log($"{clickPos.x * 24}, {clickPos.y * 24}");
        }
    }

    private void OnDrawGizmos()
    {
        Gizmos.color = Color.red;
        Gizmos.DrawWireSphere(clickPos, radius);
    }


    public void TerrianDestroy(Vector2 pos, float radius)
    {
        SpriteRenderer sr = map.GetComponent<SpriteRenderer>();
        Debug.Log(sr.sprite.pivot); 

        float x = pos.x;
        float y = pos.y;

        //
    }
}
