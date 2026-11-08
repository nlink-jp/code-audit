# E2E 第 4 走（2026-11-08）— web-fetch / standard / --prior run-1

対象: skill `0937936`（区切り (8) 済み）。`nlink-jp/web-fetch` は run-1 の所見を直した
8 コミット後（source ref `aa20666…`、clean）。standard プロファイルで Phase 0〜6 を
一周し、`--prior run-1` で持ち越し経路も通した。所見の正本は run ディレクトリの
`REPORT.ja.md`・`NEEDS-VALIDATION.ja.md`。ここには skill 側の学びだけ。

## 実行の事実

| 項目 | 値 |
|---|---|
| 予算（承認） | 54 → 64（費用ゲート 2 回: 偵察後に 54、批評者 1 が単位を 1 追加し新規候補 3 件の再検証が残った時点で +10） |
| 実績 | 56 回（reconnaissance 4、hunter 19 [16＋再依頼 3]、critic 2、verifier 19 [12＋再依頼 7]、reverifier 12） |
| 網羅単位 | 41 → 42（seed が run-1 の 37 単位を持ち越し＋run-1 後に増えた面 4: CLI の stderr エラー JSON・端末向け無害化・共有描画予算・docs 群。批評者 1 が docs 群を追加、批評者 2 が stop） |
| 持ち越し | run-1 の confirmed 6・needs_validation 1 はすべて `changed_prior`（引用元が修正コミットで変わったので再検証せず、報告書に「変更済みの前回レコード」として列挙）。rejected 9 は抑止として働き、1 件（x-user-defined の再写像）が実際に抑止された。lead 28 件を批評者に渡した |
| 候補 | 16 の主張 → 重複 4 組を `merge-candidates` で束ねて 12 fingerprint（候補率 16/42 = 0.38、定数 0.30） |
| 判定 | confirmed 6（medium 1、low 4、informational 1）、needs_validation 0、rejected 6 |
| confirmed の内訳 | `<pre>` 内の長いバッククォート列で fence の長さ決定が二次（medium、描画予算の外）; CHANGELOG のビルド機の login; CLI stderr のエラー JSON が C1・bidi 制御を無害化せずに端末へ; TOML 読み取りの寛容な文法（末尾を黙って落とす・空値を未設定扱い）; markdown リンクの text/href 無エスケープで scheme 許可リストを抜ける偽リンク; `<meta content>` の charset 解析で ToLower の長さ変化による slice panic が MCP サーバを落とす（informational: 観測なしの parser crash の規則） |
| rejected の理由 | 制御は runtime の層 1（transportError の無引用: 遠隔者は成功経路で同じ文を既に届けている）; 前提が偽 1（再帰深さ: x/net/html v0.59.0 が open-element を 512 で打ち切る）; 文書化された契約が無い 2（title の上限・ヘッダ値の起動時検証）; 自己影響 1（userinfo の echo）; 利用者に届く経路なし 1（brew の staged 変更） |
| 再検証 | keep 10・replace 2（reverifier-1: 根拠を対象内の行に置き換え; reverifier-10: 深刻度を low → informational に弱化。いずれも強化なし→直接適用、`replacements.json` に記録） |
| 許可コマンド | `go test ./...`・`go vet ./...`（両方 exit 0、offline） |
| ノート | 137（hardening 86・lead 33・out_of_scope 18） |
| run_status | complete |
| 成果物の絶対パス・ユーザー名 | なし（grep で確認） |

## 費用の実測（サブエージェント 1 本あたりのトークン）

タスク転写の最終呼び出しの文脈長（通知の `subagent_tokens` と一致することを 1 本で確認）。

| 役割 | 本数 | 平均 | 範囲 |
|---|---|---|---|
| reconnaissance | 4 | 約 132k | 101k–148k |
| hunter | 16 | 約 141k | 120k–171k |
| hunter 再依頼 | 3 | 約 156k | 144k–174k |
| critic | 2 | 約 162k | brief 187 KB / 170 KB（42 単位・prior lead 28） |
| verifier | 12 | 約 87k | 77k–107k |
| verifier 再依頼 | 7 | 約 89k | 81k–95k |
| reverifier | 12 | 約 79k | 69k–97k |

合計 約 6.2M トークン・56 回。見積もり 55〜60 回・5.5〜6M（第 3 走の記録）に対して
ほぼ一致。内訳のずれ: 候補が 13 見込みに対し 16 の主張（12 fingerprint）、再依頼が
7 見込みに対し 10（初回返答 46 本中 10 本＝22%、定数 15%。うち 6 本は親のプロンプトの
曖昧さが原因、下記）。再検証者は見積もりが数えていない（下記 E33）。

## 手順の逸脱（記録）

- 再検証（reverifier-1〜9）を批評者 1 の前に走らせた（SKILL は狩りの終了後）。簿記上の
  依存は無く、新規候補 3 件の再検証（reverifier-10〜12）は批評者 2 と並行した。
- hunter-8 は 1 回目が壊れた JSON、再依頼の 2 回目が `reviewed_paths` 欠けで 2 回続けて
  失敗 → 規則どおり `ledger.py abandon` で単位を返し、新しい hunter-15 を起動した
  （abandon 経路の初使用。費用は 3 起動で 1 単位組）。hunter-15 が charset の panic を見つけた。
- hunter-13 / hunter-14 の返答がビルド機の login を綴り、hunter-14 は監査の絶対パスも
  書いた → 「識別子は綴らず、file:line で記述する」と再依頼。verifier-3 のレコードも
  login を散文で参照したので reverifier-1 が対象内の根拠に置き換えた。
- verifier-1〜9 のうち 6 本が trace の `kind` / `scope` を落とした。親のプロンプトが
  「file, line, description」だけを挙げたのが原因で、`brief verifier` の `required_fields`
  にも trace_entry / evidence_entry の必須欄は無い → 6 本を再依頼（`count --rerun`）。
  verifier-18 は rejected レコードの `coverage_ids` を落として再依頼。
- verifier の id は 9 の次が 16（新規候補の検証者を候補単位の数で先に番号づけした）。
  id の連番は契約ではないので簿記上の問題は無い。
- hunter-16（docs 群）が「Glob / Grep が使えない」と報告し、ファイル名を推測して読んだ
  （docs 配下 8 ファイルすべてを読んでいたことは親が `find` で確認、批評者 2 も確認）。
  第 2 走の recon-c/d・hunter-12 と同じ事象。
- Explore 型の shell 使用の自己申告: verifier-16（stdlib の grep）、verifier-18（sed /
  grep / cat 1 回）、hunter-16（skill の schema.json への grep）。いずれも読み取り専用と申告。残余。
- 報告書の置換行が「文言・行番号の修正のみ、強化なし」と出たが、reverifier-10 の置換は
  深刻度の弱化（low → informational）だった（下記 E35）。
- 親の補助スクリプト（zsh）で `set -- $v` と未引用 `$VAR` が語分割されず、
  「no task for …」や fingerprint の二重指定を起こした。skill の問題ではない。

## 学び → 区切り 9 の候補

| # | 事象 | 直し方（案） |
|---|---|---|
| E29 | （第 3 走から持ち越し）`</target-data>` の閉じタグが固定で偽造できる | 閉じタグにも nonce（`</target-data-N>`）。全プロンプトの約束を変えるのでこの区切りで判断 |
| E30 | 前回 needs_validation のレコードが修正で `changed_prior` になったのに、単位の `prior_status` は `prior_needs_validation` のまま | `seed --prior` は confirmed と同じく `prior_needs_validation_changed_source` を付ける |
| E31 | 検証者 6 本が trace の `kind` / `scope` を落とした（親の文言の曖昧さ） | `brief verifier|reverifier` の `required_fields` に `trace_entry` / `evidence_entry` の必須欄を含め、SKILL の検証者プロンプトは brief の欄名を列挙する |
| E32 | ハンター 2 本の返答がビルド機の login と監査の絶対パスを綴った | 全役の契約に「個人識別子・ローカルパスは綴らず file:line で記述」。`ledger.py record` / `findings.py add` は返答に実行者の login（`getpass.getuser()`）または絶対ローカルパスを含むとき拒む（スクリプトが守る） |
| E33 | `estimate` が standard の再検証者を数えない（`reverifiers: None`） | 決定済み＋見込み候補の数を再検証者として足す |
| E34 | リスト不能を報告するハンターがファイル名を推測して読む（第 2 走・第 4 走） | `brief hunter` が `starting_paths` 配下のファイル一覧（対象内・相対パス・上限つき）を印字する |
| E35 | 報告書の置換行が弱化の置換を「文言の修正のみ」と書く | `compile.py` は `replacements.json` の差分種別（文言 / 弱化）で文を分ける |
| E36 | 2 回続けて失敗したハンターの放棄と新規ハンターの起動が 3 起動かかった | 規則どおり。見積もりの再依頼率に「放棄 1 件」を含めるかは費用の実測を待つ（今回 56/64） |

検証者の働きは設計どおり: hunter が confirmed と言った候補のうち verifier が rejected に
倒したのが 4 件、needs_validation と言った 3 件は confirmed 1（charset の panic: 標準ライブラリ
と x/net/html の読解で決着）・rejected 2（再帰深さ: 依存先の source で前提が偽; 無引用: 制御は
runtime の層）。rejected 6 件はすべて hardening に格下げ。再検証者は 12 件中 2 件を置換
（弱化と文言のみ）し、強化は 0。

## Phase 3 の総括（4 走）

| 走 | 対象 / profile | 起動 | トークン | confirmed / nv / rejected |
|---|---|---|---|---|
| 1 | webhook-relay / quick | 29 | 約 2.6M | 5 / 2 / 7 |
| 2 | webhook-relay / standard --prior | 42 | 約 3.9M | 0 / 2 / 7 |
| 3 | web-fetch / quick | 43 | 約 4.6M | 6 / 1 / 9 |
| 4 | web-fetch / standard --prior | 56 | 約 6.2M | 6 / 0 / 6 |

standard の 2 走はいずれも見積もりの範囲に収まった（第 2 走は 2/3、第 4 走はほぼ一致）。
quick → standard の持ち越しは第 4 走で初めて同一 profile 系列で働き、run-1 の rejected が
1 件の再報告を抑え、修正済みの 7 件は再検証を費やさず「変更済み」として列挙された。

## 区切り (9) での採用（2026-11-08）

E29〜E35 を採用した（101 テスト緑）。E36 は実測待ちで据え置き。E29: `run.py nonce` が開きと閉じの
両タグを印字し、SKILL は `<target-data-N>…</target-data-N>` で包む（architecture.md 側の閉じタグ
潰しはそのまま残す）。E30: `seed --prior` が `prior_needs_validation_changed_source` を付ける。
E31: verifier / reverifier の brief が `trace_entry`・`evidence_entry` の必須欄も印字し、SKILL の
契約は brief の欄名を引く。E32: `_contract.personal_identifier_errors`（実行者のログインを
3 文字以上のとき単語一致で、絶対ローカルパスを正規表現で）を `record`・`merge-critic`・
`architecture`・`findings.py add`・`note` の入口で走らせ、全役の契約に「綴らず file:line で記述」。
E33: standard の見積もりに決定済みレコード 1 件あたり再検証者 1 を足す（起動済みは引く）。
E34: `brief hunter --target TARGET` が単位の starting_paths 配下のファイル一覧を運ぶ（上限 400、
リンクは名前のみ、`.git` は除く）。E35: `findings.py add --replace` が `weakened` を記録し、
報告書の置換行は強化・弱化・文言を分けて数える。
