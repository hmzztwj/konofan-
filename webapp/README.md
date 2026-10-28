# ローカル版クライアント（webapp）

「この素晴らしい世界に祝福を！ ファンタスティックデイズ」の**解析済みデータで動く、ローカルの遊べるクライアント**です。
公式クライアントの復元ではなく、MasterData（数値・テキスト）と書き出したアートを使って**遊びのループを再構成**したものです。

## 起動

```bash
# 1) データと画像を生成（初回のみ・数秒）
python tools/build_webapp.py

# 2) ブラウザで開く（file:// でそのまま動きます）
start webapp/index.html
```

`webapp/data.js`（8MB, `window.KD`）と `webapp/img/`（ハードリンク）は生成物なので Git 管理外です。

## いま遊べるもの（v0.1）

| 画面 | 状態 | 中身 |
|---|---|---|
| ホーム | ✅ | 統計・ナビ |
| 冒険（メインクエスト） | ✅ | 43 エリア / 1,083 ステージ、クリアで次が解放、進行は localStorage |
| 編成 | ✅ | 617 枚から 3 枚を選択、Lv24 時点のステータス表示 |
| バトル | ✅ | 3 WAVE / 速度順のターン制 / 通常攻撃・スキル2種・必殺技 / SP 共有ゲージ / ダメージ表示・戦闘ログ |
| メンバー | ✅ | ★4 342 / ★3 202 / ★2 48、カード詳細（ステータス・スキル・パッシブ） |
| 資料庫 | ✅ | 既存の `site/`（データ表・CG・シナリオ）へリンク |

## データの出どころ

- `out/masterdata/*.json` — 復号済み MasterData 279 表（`tools/decrypt_masterdata.py`）
- `out/assets_sorted/` — UnityCache から書き出した 21,790 枚（`tools/extract_assets.py`）
- 使用テーブル: `member` / `character` / `skill_ac` / `skill_ac_details` / `skill_sp` / `skill_sp_details` / `skill_enemy_details` / `battle_enemy` / `battle_enemy_ai` / `battle_wave` / `mainquest_stage` / `mainquest_area` / `text` / `assetname`

## 戦闘式（近似）

元クライアントの定数は非公開なので、MasterData の値から**それらしい式**を組んでいます（`app.js` の `damage()`）。

```
基礎 = (物理 ? ATK : M.ATK) × 威力% / 100
軽減 = 基礎 × 420 / (420 + 防御)
最終 = 軽減 × (0.95〜1.05) × (会心 8% のとき 1.6)
```

- プレイヤー Lv は暫定 24（`PLV`）。ステータスは `member.min_*` 〜 `max_*` を線形補間。
- SP は共有ゲージ（最大 10、開始 3）。通常攻撃 +1、スキル −2、必殺 −5。
- 敵 AI は `battle_enemy_ai` の weight でスキル選択。

## これから（未実装）

1. **育成**: レベル/限界突破/スキルレベル（`member_lv_exp` / `member_limitbreak_*`）
2. **ガチャ**: `gacha` 系テーブル + 提供割合テーブルから抽選、演出は簡易
3. **アイテム/交換所/ミッション**: `item` / `exchange_item` / `pack` / `quest_mission`
4. **アリーナ・ギルド等の対人/共闘**: 元がサーバー前提のため、ローカルでは簡略版のみ
5. **音声・BGM**: `bundles/Cri/Cpk` 内の HCA を取り出して再生（`tools/cpkg` 相当の作業が必要）

## 既知の制限

- 本副本のキャッシュは部分的なので、**バトル背景 26/27・敵グラ 63/229** しか画像が無い（無い場合はシルエット表示）。
- スキル名・効果テキストは `text`/`assetname` にあれば日本語、無ければ ID のまま。
- セーブはブラウザの localStorage のみ（`kd_party` / `kd_cleared`）。
