# E2E 第 2 走（2026-11-08）— webhook-relay / standard / --prior run-1

対象: skill `564e4d9`（区切り (6) 済み）。`nlink-jp/webhook-relay` は run-1 の所見を
直した 11 コミット後（source ref `e93c6b1…`、clean）。standard プロファイルで
Phase 0〜6 を一周し、`--prior run-1` で持ち越し経路も通した。所見の正本は run
ディレクトリの `REPORT.ja.md`・`NEEDS-VALIDATION.ja.md`。ここには skill 側の学びだけ。

## 実行の事実

| 項目 | 値 |
|---|---|
| 予算（承認） | 63 回（見積もりどおり） |
| 実績 | 42 回（reconnaissance 4、hunter 16 [15＋再依頼 1]、critic 4 [3＋再依頼 1]、verifier 9、reverifier 9） |
| 網羅単位 | 34 → 37（批評者 1 が 2 追加・1 再割当て、批評者 2 が 1 追加、批評者 3 が stop） |
| 候補 | 9（重複なし） |
| 判定 | confirmed 0、needs_validation 2（egress の主張は NAT の有無に依存; X-Forwarded-For の複数行をフロントエンドがどう束ねるか）、rejected 7（すべて hardening に格下げ） |
| 再検証 | keep 8・replace 1（文言と行番号のみ、強化なし→直接適用、`replacements.json` に記録） |
| 許可コマンド | `go test ./...` 1 本（E6 の GOCACHE 転送で 14 秒・緑・ネットワークなし）。多くの check が `existing_test` を根拠にできた |
| 持ち越し | run-1 のレコード 14 件はすべて `unlinked_prior`（quick→standard で coverage_id の subsystem 欄が合わない）。lead ノートは run-1 に無く 0 |
| ノート | 115（hardening 89・lead 15・out_of_scope 11） |
| run_status | complete |
| 成果物の絶対パス・ユーザー名 | なし |

## 費用の実測（サブエージェント 1 本あたりのトークン）

| 役割 | 本数 | 平均 | 範囲 |
|---|---|---|---|
| reconnaissance | 4 | 約 101k | 94k–114k |
| hunter | 15 | 約 100k | 82k–176k（リポ全体＋連鎖の 2 単位を持った hunter-13 が 176k） |
| critic | 3 | 約 117k | 113k–120k（brief 110〜130 KB を読む） |
| verifier | 9 | 約 86k | 74k–96k |
| reverifier | 9 | 約 70k | 63k–83k |
| 再依頼 | 2 | 約 107k | 96k–118k |

合計 約 3.9M トークン・42 回。見積もり 63 回・6.3M に対し 2/3。差の内訳: 候補が
17 見込みに対し 9（0.26/単位）、再依頼が 10 見込みに対し 2（初回返答 40 本中 2 本＝5%、
区切り (6) の契約文の明記が効いた）。

## 手順の逸脱（記録）

- Phase 4 の検証を狩りの波と並行して走らせた（SKILL は波の終了後）。簿記上の依存は
  無く、批評者の再割当て規則（pending 候補を持つ単位は再割当て不可）にはむしろ有利。
- ハンターへの入力は `agents/briefs/hunter-N.md`（親が台帳とクラス本文から生成）を
  ファイル参照で渡した。再検証者の入力も同様に親が findings.json から組んだ。
  `ledger.py brief` には hunter / reverifier の役が無い。
- 批評者 2 の初回返答は `priority` が文字列・class 参照に `%20` で拒否→再依頼。
  hunter-2 は reviewed_paths の欠け 1 件で再依頼。いずれも `count --rerun` で記帳。
- recon-c/d・hunter-12 が「Glob/Grep が無い」と報告（Explore 型のツール提供が不均一）。
  hunter-8/9・reverifier-4/8 は読み取り専用の shell を 1 回使ったと自己申告（残余リスク、再確認）。

## 学び → 区切り 7 の候補

| # | 事象 | 直し方（案） |
|---|---|---|
| E13 | quick の prior は standard で全件 `unlinked_prior`（subsystem 欄の差） | `seed` が prior の profile が quick なら surface×boundary×class で突き合わせる |
| E14 | 批評者が追加した単位の `prior_status` が `none`（prior があるのに） | `merge-critic` は prior の有無で `new` を入れる |
| E15 | `brief` に hunter と reverifier の役が無い | `brief hunter --agent`（割り当て単位＋クラス本文）、`brief reverifier --fingerprint`（レコード＋単位＋ログ、検証者の層分析は含めない） |
| E16 | 批評者が `priority` を文字列・class 参照を `%20` で返す | 批評者の契約文に「整数」「見出しの綴りそのまま」を明記（validator は既に拒む） |
| E17 | 報告書の置換行「いずれも別の新しい検証者が確認」が強化 0 件でも出る | 強化件数が 0 のとき文を変える |
| E18 | 見積もりの候補率 0.5/単位は過大（実測 0.26）、再依頼率 20% も過大（実測 5%） | 2 走の実測で 0.35 / 10% に置く（quick 1 走と standard 1 走の中間） |
| E19 | 検証と波の並行は有効 | SKILL に「波の間に候補を検証してよい」と明記 |
| E20 | 批評者の brief が 110〜130 KB（37 単位） | checks の `result` を要約せず全部載せる現行は妥当だが、単位数が増えると限界。`brief critic --since-wave N` で前波以降の差分だけにする案 |

検証者・再検証者の働きは設計どおり: 9 候補のうち確定は 0 で、7 件は severity.md
「所見でないもの」（運用者の自己影響・配備の推測）で退け、2 件は決定的な配備事実を
blocker に挙げた。run-1 の 5 件の確定所見は修正済みで、standard でも再発を見ていない。

## web-fetch 2 走の見積もり（E18 の定数で）

| 走 | 規模の根拠 | 呼び出し（概算） | トークン（概算） |
|---|---|---|---|
| web-fetch quick | Go 6.2k 行・41 ファイル、MCP サーバ class が加わる → 単位 50〜60 | 4＋18〜20＋1＋18〜21＋再依頼 4 ≈ 45〜50 | 4.5〜5M |
| web-fetch standard | 同上・2 段検証・critic 3 | 4＋20＋3＋40＋再依頼 7 ≈ 75 | 7.5M |
