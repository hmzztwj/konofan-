# 02 · MasterData 加密与密钥

## 形态

`Data/MasterData/*.data` 全部是 **base64 文本**；解码后长度恒为 16 的倍数，熵 7.26–7.96。

## 密码学判定（排除法）

| 实验 | 结果 | 结论 |
|---|---|---|
| ECB 重复块 | assetname.data 395,031 块 / 0 重复 | 不是 ECB |
| 同前缀文件两两 XOR | 熵 7.83–7.99，接近随机 | 不共享 keystream（非 CTR/OFB/固定 nonce） |
| 尾部对比 | 每个文件末尾都不同 | 非"ECB + 固定 padding 块" |
| 自相关 offset 1..64 | ≈0.004（随机 0.0039） | 无重复异或密钥 |
| 前 16 字节 | 十二个前缀分组，最大一组 155/279 相同 | **固定 IV 的 CBC**，明文首块按表族相同 |

## 代码路径（IL2CPP）

```
MasterDataManager.LoadLocalJsonMaster<T>(string dataName)      RVA 0x40A0950
  └─ LocalDataSaveUtil.LocalLoad<object>                       0x2E18F8C(LocalLoadImpl)
       └─ AesEncryption.DecryptString(string, bool)            RVA 0x2E80AC8
            ├─ Path.Combine → File.Exists → StreamReader.ReadToEnd
            ├─ RijndaelManaged..ctor（默认 256/128）
            ├─ Key/Iv 为空 → GenerateKeyFromPassword(256, &Key, 128, &Iv)   0x2E803A0
            ├─ set_Key / set_IV
            └─ Convert.FromBase64String → CreateDecryptor → 解密
```

`GenerateKeyFromPassword` = `PBKDF2-HMAC-SHA1(Pass, UTF8(Salt), 1000)` 取 32B 当 Key、再取 16B 当 IV；
`Pass = TextUtil.a1 + TextUtil.b5`，`Salt = TextUtil.df`（三个 ObscuredString 字段）。

## 为什么静态推导是错的

按上面公式算出的 key（`c195571f…` / IV `544f7ac8…`）**解不开任何真实文件**。
原因：`TextUtil` 里那 76 个高熵二字母属性是**UI 文本模板**，不是密钥材料。
穷举也证明了这点：19,656 条字面量 × 7 种盐、76 个 token 两两拼接（438,900 次 PBKDF2）、
.so 里 2,800 万个 8 字节对齐窗口——**全部 0 命中**。

## 正确的取法：从运行中的进程里读

跑起来以后 `AesEncryption.static_fields[0]` 就是 Key，`[8]` 是 Iv（两个 `byte[]`）。

```
1. /proc/<pid>/maps                → libil2cpp.so base = 0x400022c00000
2. 槽 0x6850940 (AesEncryption_TypeInfo) 运行时地址 = base + 0x6850940
3. class = [槽]                    → 0x71bf524013c0
4. static_fields = class + 0xB8    → 0x71c33b1b1d90
5. [static_fields+0] = byte[] Key：长度在 +0x18、数据在 +0x20 → len 32
   [static_fields+8] = byte[] Iv：len 16
```

读内存：`dd if=/proc/<pid>/mem bs=<n> iflag=skip_bytes,count_bytes skip=<addr> count=<n> | od -An -tx1`

脚本：`tools/read_key_runtime.py`（接 adb，全自动）。

## 结果

```
key = 851c20916d7a895bc14ceba139e3dc253486b30b858140c41c8a7e9fe99aec72
iv  = dcaa69cc863200d4eb74b4980bd60383
```

279 / 279 个文件解开，明文 102 MB，结构统一为 `{"master":[...],"version":"..","status":0}`。
**跨构建恒定**：mod 版、去 mod 版、2024-10 的用户快照生成的文件都能互解（相同前缀 ⇒ 相同 key）。

## 附带结论

- `ShaEncryption` 是同命名空间下的另一个类，专职 **CRI 文件名加密**（见 `docs/03`）。
- `DecryptString(string, ObscuredString key, ObscuredString iv)` 重载 **0 个调用者**，
  主数据只走静态 Key/Iv 那一版。
