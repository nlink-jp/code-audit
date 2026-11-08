# E2E 第 3 走（2026-11-08）— web-fetch / quick

対象: skill `cc04ab7`（区切り (7) 済み）。`nlink-jp/web-fetch`（source ref
`bdc77d3…`、clean）。quick プロファイルで Phase 0〜6 を一周。prior なし。
所見の正本は run ディレクトリの `REPORT.ja.md`・`NEEDS-VALIDATION.ja.md`。
ここには skill 側の学びだけ。

## 実行の事実

| 項目 | 値 |
|---|---|
| 予算（承認） | 34 → 41 → 43（費用ゲート 3 回: 偵察後に 34、候補 16 件が出て +7、再依頼で枯渇して +2） |
| 実績 | 43 回（reconnaissance 4、hunter 18 [14＋再依頼 4]、critic 1、verifier 20 [16＋再依頼 3＋新規 1]） |
| 網羅単位 | 37 → 38（最終批評者が 1 追加＝quick なので deferred: 取得内容からの panic 到達性。recover が入口経路に無いのは hunter-14 が確認） |
| 候補 | 16（重複 1: hunter-3 と hunter-12 の userinfo の主張は `record` が同一 fingerprint として束ねた） |
| 判定 | confirmed 6（medium 1、low 5）、needs_validation 1、rejected 9 |
| confirmed の内訳 | 入れ子 blockquote / list の接頭辞による描画サイズの増幅（medium）; `-trimpath` 無しの release ビルド; linux tar の owner 名; CLI が取得テキストをエスケープ列ごと端末へ印字; README の「プロジェクトの MCP 設定は LAN を開けない」の約束と相対 XDG_CONFIG_HOME の受理（verifier が主張を狭めて確定）; `<base href="javascript:">` が scheme フィルタを抜ける |
| needs_validation | isError の message に遠隔の Content-Type を無引用で挿入（runtime の nonce wrap が isError にも及ぶかが決める） |
| rejected の理由 | 制御は runtime の層 3（config の link/owner 検査、内部 DNS の開示、NAT64 の網固有接頭辞）; 文書化された契約が無い 3（cache の 3 倍、title の上限、x-user-defined の再写像）; 自己影響 1（userinfo の echo）; 前提が偽 1（zone つき応答: 標準ライブラリが zone を落とす）; 利用者に届く経路なし 1（brew formula のゲート） |
| 許可コマンド | `go test ./...`・`go vet ./...`（両方 exit 0、E6 のキャッシュ転送で offline） |
| ノート | 112（hardening 72・lead 28・out_of_scope 12） |
| run_status | complete |
| 成果物の絶対パス・ユーザー名 | なし |

## 費用の実測（サブエージェント 1 本あたりのトークン）

| 役割 | 本数 | 平均 | 範囲 |
|---|---|---|---|
| reconnaissance | 4 | 記録なし（通知が文脈圧縮の前で失われた） | 第 2 走の約 101k を仮定 |
| hunter | 14 | 約 112k | 89k–186k（リポ全体＋秘密情報の 2 単位を持った hunter-14 が 186k・39 回のツール呼び出し） |
| hunter 再依頼 | 4 | 約 140k | 107k–193k |
| critic | 1 | 約 144k | brief 152 KB（37 単位・候補 16・uncovered 11） |
| verifier | 17 | 約 99k | 69k–124k |
| verifier 再依頼 | 3 | 約 95k | 72k–110k |

合計 約 4.24M（偵察を除く実測）＋偵察 約 0.4M（仮定）≈ 4.6M トークン・43 回。
見積もり 34 回・3.4M に対し約 1.3 倍。差の内訳: 候補が 13 見込みに対し 16（0.43/単位、
定数 0.35）、再依頼が 2 見込みに対し 7＋新規 1（初回返答 36 本中 7 本＝19%、定数 10%）。

## 手順の逸脱（記録）

- `architecture.md` を書かず、ハンターには偵察の要約をプロンプトに直書きした。批評者の
  段で露見し、偵察 4 返答から機械的に Markdown を組んで補った（E21）。
- 検証はハンター 14 本の記帳後に始めた（波との並行なし）。
- 再依頼の内訳: hunter-4（evidence に未知キー `scope_note`）、hunter-5（JSON の閉じ括弧
  過多）、hunter-8 / hunter-14（`reviewed_paths` の欠け）、verifier-12 / verifier-15
  （末尾の `}` 余り）、verifier-13（1 回目: rejected の必須欄 `description`・`evidence`
  欠け; 2 回目: evidence にモジュールキャッシュのパス → digest が拒否）。verifier-13 は
  2 回続けて失敗したので規則どおり新しい verifier-17 を起動した（rejected、同じ結論）。
- Explore 型の shell 使用の自己申告: hunter-14（schema.json への grep）、verifier-2
  （GOROOT への grep）、verifier-10（class 本文の grep）、verifier-14（ls / grep / sed /
  cat / `python3 -c`）。いずれも読み取り専用と申告。残余（SKILL に記載済み）。

## 学び → 区切り 8 の候補

| # | 事象 | 直し方（案） |
|---|---|---|
| E21 | 親が `architecture.md` を書き忘れ、ハンターには直書きした | `ledger.py brief` は `RUN/architecture.md` が無ければ拒む。`ledger.py architecture RUN` が `agents/recon-*.json` から Markdown を組む（簿記はスクリプト） |
| E22 | `brief critic|verifier` の候補に `proposed_verdict`・根本原因が載らない（None） | `record` が候補の `proposed_verdict` と `root_cause` / `claimed_root_cause` を待ち行列に保存し、brief が印字する（SKILL は「brief に載る」と書いている） |
| E23 | 壊れた JSON の返答が 36 本中 3 本（括弧の過不足） | 保存の失敗時に失敗位置の前後 60 字を印字し、再依頼文に貼れるようにする（位置と前後を添えた再依頼は毎回 1 発で直った） |
| E24 | 検証者が rejected の必須欄を落とす・対象外ファイルを evidence に書く | 検証者の契約に「判定ごとの必須欄」と「trace / evidence の file は対象内のみ。依存先・標準ライブラリの引用は散文に」を明記。`brief verifier` が schema から必須欄一覧を印字 |
| E25 | 批評者の起動後も `estimate` が critics=1 を数え、候補 17 を見込む（pending は 16） | 起動済みの批評者を引き、狩りが終わったら pending の実数を使う |
| E26 | 費用ゲートを走の途中で 2 回追加した（34 → 41 → 43） | 候補率は quick 0.43〜0.48、standard 0.26 と二極: プロファイル別の定数（quick 0.45 / standard 0.30）、再依頼 15%。SKILL に「不足が確定した時だけゲートを再び通る」を明記 |
| E27 | リポ全体＋秘密情報の単位を持った hunter-14 が 29 ファイルを読み 186k | リポ全体の単位は 1 単位 1 ハンターで割り当て、`starting_paths` はツリーの上位だけにする |
| E28 | 検証者 3 本が GOROOT・モジュールキャッシュを読んで hunter の blocker を解いた（zone つき応答・`ResolveReference` の分岐・htmlindex の表） | 「対象の go.mod が固定する版の依存先と GOROOT の読解は許す。引用は散文で、版を明記」を検証者の契約に書く |

検証者の働きは設計どおり: hunter が confirmed と言った 8 件のうち confirmed 5
（1 件は主張を狭めて確定）、hunter が needs_validation と言った 3 件は nv 1・confirmed 1
（`<base href>`: 標準ライブラリの読解で決着）・rejected 1。9 件の rejected はすべて
hardening に格下げ。

## web-fetch standard 走の見積もり（E26 の定数で）

| 項目 | 概算 |
|---|---|
| 単位 | 38（deferred 1 を含む）＋批評者 2〜3 の追加 |
| 持ち越し | run-1 の confirmed 6・needs_validation 1 を先に再検証、rejected 9 は同じ主張を抑止 |
| 呼び出し | 4＋hunter 13〜14＋critic 3＋verifier 12〜14＋reverifier 13〜15＋再依頼 15% ≈ 55〜60 |
| トークン | 約 5.5〜6M |

## 区切り (8) での採用（2026-11-08）

E21〜E28 をすべて採用した（97 テスト緑）。E21〜E26 はスクリプト: `ledger.py architecture RUN` が
`agents/recon-*.json` から `architecture.md` を組み（絶対ローカルパスを含む返答は拒む）、
無ければどの役の `brief` も印字しない。待ち行列は hunter の判定案を `verdict` に持っていたので、
brief が `proposed_verdict` と根本原因として印字する。`brief verifier` は schema から判定ごとの
`required_fields` と `file_rule` を印字する。`read_json` は失敗位置の前後 60 字を印字する。
見積もりは起動済みの批評者を引き、狩りが終われば待ち行列の実数を使い、定数は quick 0.45 /
standard 0.30・再依頼 15%。E27（リポ全体の単位は単独割り当て）、E28（固定版の依存先と GOROOT の
読解を許し、引用は散文で）、費用ゲートの再通過（帳簿が不足を示したときだけ 1 回）は SKILL.md の文言。
