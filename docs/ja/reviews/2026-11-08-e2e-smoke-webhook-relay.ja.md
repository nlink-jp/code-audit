# E2E スモーク（2026-11-08）— webhook-relay / quick

対象: skill `cac8de8`（検証 2 巡の修正済み）。組織の実リポジトリ
`nlink-jp/webhook-relay`（source ref `5ba3625b…`、作業ツリー clean）を
`quick` プロファイルで一周させ、Phase 0 から 6 までを SKILL.md の手順どおりに
親（本人のセッション）が運転した。目的は (1) スクリプトと手順が実リポで通るか、
(2) 一周の費用を実測して残り 3 走（web-fetch quick / standard、webhook-relay
standard）の見積もりを置き直すこと。所見の中身は run ディレクトリの
`REPORT.ja.md` が正であり、ここには skill 側の学びだけを残す。

## 実行の事実

| 項目 | 値 |
|---|---|
| 予算（承認） | 34 回 |
| 実績 | 29 回（reconnaissance 5 [実 4]、hunter 10 [実 7＋再依頼 3]、critic 2 [実 1＋再依頼 1]、verifier 12 [実 11＋再依頼 1]） |
| 網羅単位 | 21 → 26（批評者が 5 件を deferred で追加、1 件を再割当て→deferred） |
| 候補 | 14（うち同根の重複 3 対） |
| 判定 | confirmed 5（medium 1 / low 4）、needs_validation 2、rejected 7（重複 3、hardening に格下げ 4） |
| 許可コマンド | 0（`go test` は network・ADC・HOME 配下の build cache に触れる） |
| run_status | complete |
| 成果物の絶対パス | なし（`/Users/<login>/...` は検証者の例示のみ） |

## 費用の実測（サブエージェント 1 本あたりのトークン）

| 役割 | 本数 | 平均 | 範囲 |
|---|---|---|---|
| reconnaissance | 4 | 約 88k | 82k–98k |
| hunter | 7 | 約 86k | 69k–136k（repo 全体を読む単位が 136k） |
| critic | 1 | 約 100k | — |
| verifier | 11 | 約 91k | 81k–102k |
| 再依頼（SendMessage 継続） | 5 | 約 100k | 73k–146k（文脈を再送するため初回より高い） |

一周の合計は約 2.6M トークン。初回返答の拒否率は 24 本中 5 本（21%）で、
その再依頼が合計の約 2 割を占めた。

## 手順の逸脱（記録）

- recon-d を二重に記帳した（`count` は減らせない設計）。実 4 本、記帳 5 本。
- recon-d の `files` に絶対パスが混ざり、保存時に相対化した。
- 批評者への入力で網羅単位を番号で示し、`coverage_id` の文字列を渡さなかった。
  返りの `reassign_ids` が「17」になり `merge-critic` が拒んだ。再依頼で解消。
- 重複 3 対は 1 人の検証者に両方を渡し、`verdicts: [...]` の配列で返させた。
  この形は契約外のため、親が `agents/to-add/` に 1 record ずつ切り出してから
  `digest` → `add` を通した（親側の抽出）。
- 検証者と批評者の契約は、SKILL.md が貼り付けを求める schema 片を
  ファイル参照（`schema.json` のパート名）で渡した。

## 学び → 区切り 6 の候補

| # | 事象 | 直し方（案） |
|---|---|---|
| E1 | `count --agent` が同じ id を黙って二重記帳する | 既登録 id は再依頼フラグなしでは拒む |
| E2 | recon が絶対パスを返す | recon の契約に「repository-relative のみ」を明記、`record`/保存側で拒む |
| E3 | hunter の `reviewed_paths` ≠ checks の和集合で 2 本拒否 | `record` が ⊇ を受けて和集合を保存する、または契約文を直す |
| E4 | `.gitignore:…` の fingerprint が先頭 `.` で拒否 | FINGERPRINT_RE で dot-file を許す |
| E5 | `estimate` が単位ごとに hunter 1 本と数え過大 | 計画の束ね（3–4 単位/本）を見積もりに反映 |
| E6 | Go 対象は境界の下で `existing_test` を一切作れない | `run.py exec` が run 配下の GOCACHE を用意し、その書込だけ許す |
| E7 | 同根の候補が複数 hunter から別 fingerprint で届く | `ledger.py merge-candidates`（検証前に統合、重複は rejected 記録）か、`add` が `verdicts[]` を受ける |
| E8 | 批評者に台帳を言い換えて渡せてしまう | `ledger.py brief critic` が批評者入力（coverage_id 原文つき）を印字する |
| E9 | 検証者の trace に sink が 2 つ | 契約文に「sink は最後の 1 件」を明記（validator は既に拒む） |
| E10 | cli.md に「Refines generic `…`.」の残骸 2 箇所 | 削除 |
| E11 | 検証者の notes に次走の lead が混ざる（bucket 名の squatting、`--set-env-vars` のカンマ分割、zip の uid/gid） | note kind に `lead` を足し、次走の `seed` が拾う |
| E12 | `decide` 後も単位は `candidate` のまま | 報告書で「candidate（判定済）」と読めるようにする |

検証者は設計どおりに働いた: hunter の confirmed 4 件を severity.md「所見でないもの」
を引いて rejected＋hardening note に格下げし、needs_validation 2 件はいずれも
ライブラリ事実（storage v1.62.0 の `Writer.Close` の意味）を blocker に挙げた。

## 残り 3 走の見積もり（実測から）

| 走 | 規模の根拠 | 呼び出し（概算） | トークン（概算） |
|---|---|---|---|
| webhook-relay standard | 同じ 21＋6 単位、hunter 2 波、critic 2、再検証あり | 40–45 | 3.5–4M |
| web-fetch quick | Go 6.2k 行（webhook-relay の 4 倍）、MCP サーバ class が加わる | 35–40 | 3.5M |
| web-fetch standard | 同上の standard | 60–70 | 6M |

再依頼率 21% を含む。区切り 6 の E3・E4・E8・E9 を先に直せば再依頼は
半分以下に落ちる見込み。
