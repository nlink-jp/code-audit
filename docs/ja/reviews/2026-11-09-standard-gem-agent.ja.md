# 実戦投入 第 1 走（2026-11-09）— gem-agent / standard / prior なし

対象: skill v0.1.0（区切り (9) 済み）。`nlink-jp/gem-agent` は ADR 108 本を持つ
LLM エージェントランタイム（source ref `a033b76…`、clean）。別セッションが standard
プロファイルで Phase 0〜6 を回し、所有者（同じ利用者）が所見をトリアージして
v0.100.0 / v0.100.1 を出した。所見の正本は run ディレクトリの `REPORT.ja.md`・
`NEEDS-VALIDATION.ja.md`、所有者側の判断は gem-agent の ADR-0109〜0113。ここには
skill 側の学びだけ。

## 実行の事実

| 項目 | 値 |
|---|---|
| 予算（承認） | 140（見積もりは候補率 0.30 で約 86。途中で引き上げた） |
| 実績 | 138 回（reconnaissance 4、hunter 27、critic 1、verifier 55、reverifier 51） |
| 網羅単位 | 71（prior なし。すべて fresh） |
| 判定 | confirmed 37（high 2、medium 8、low 23、informational 4）、needs_validation 9、rejected 7、統合 9 |
| 候補率 | 判定済 53 ＋未判定 1 ＋統合 9 ＝ 63 の主張 / 71 単位 ＝ 0.75 以上（定数 0.30 の 2 倍超） |
| 再検証 | 置換 10（弱化 1・文言 9、強化 0） |
| ノート | 287 |
| run_status | **incomplete**（`budget_reserved_for_verification`: candidate 43 のうち判定済 42、blocked 1、未割当の面 16） |
| 所有者の処置 | high 1 件を**仕様**と判断して取り下げ（ADR-0110）、medium 3 件を理由つきで**受け入れ**（ADR-0113）、残りは v0.100.0 / v0.100.1 で修正 |

## 所見の扱いで分かったこと

- **high の 1 件は文書化された仕様だった。** 「`-p` なしのパイプ stdin が `!` を含めて
  操作者の入力として走る」は ADR-0055 §3 が決めたスクリプト経路で、操作者が自分で
  パイプを組まない限り何も起きない（`curl … | bash` と同じ形）。所有者は拒否と
  `--script-stdin` フラグを実装し、レビューを 2 回通してから取り下げた。検証者の
  レコードは `intended_behavior` に「documented choice」と書きながら high を付けていた。
  問うべきは 2 つ: 誰の行為で成立するか、その動作を決めた記録はあるか。
  （knowledge development-process「監査の所見を直す前に、誰の行為で成立するかと、
  仕様かどうかを問う」）
- **medium 3 件は理由つきで受け入れられた**（`agentic_file_search` 内の読み取りは
  フック・always の外 / 祖先 AGENTS.md は信頼確認の外 / ファイルツールの判定と書き込みの
  リンク差し替え）。所有者は ADR-0113 に残余として記録し、操作者の読む場所に明記した。
  次走で `--prior run-1` を渡すと、これらは `prior_confirmed_same_source` として
  再検証に回り、同じ所見が再報告される — 受け入れを帳簿に書く場所が無かった。
- **直すのが正しかった high**（承認済みレーンのキャッシュが read レーンの書ける場所に
  ある）は、誰の行為も要らず ADR-0084 の保証を破っていた。同じ 2 問で区別できる。
- **予算を使い切って incomplete。** 候補率の定数 0.30 は「prior のある standard」
  2 走で較正したもので、prior のない standard は quick と同じく全単位が fresh。
  実測は 0.75 以上（quick の fresh は 0.43・0.48）。71 単位の大きいリポでは差が
  50 回分になった。
- knowledge には同じ日に新しい教訓が 4 件入った（上記の問い、特権ビルドのキャッシュの
  置き場所 — 既存クラスの出典「session scratch へ」は不十分だったと実測、承認プロンプトは
  呼び出し全体、再開で再利用するディレクトリのリンク拒否）。RFP の方針どおりクラスで追随する。

## 学び → 区切り 10 の候補

| # | 事象 | 直し方（案） |
|---|---|---|
| E37 | 操作者が組む経路の文書化された動作に high が付いた | confirmed レコードに `path_actor`（unasked / operator_composed）と `specified_in`（決めた記録、無ければ none）を必須にし、operator_composed かつ記録ありは所見でない（規則 3: `findings.py add` が拒む → rejected と `documentation` ノート） |
| E38 | 見積もりが prior のない standard を quick の半分の候補率で見積もり、140 回でも足りなかった | 候補率をプロファイルでなく「単位に prior があるか」で分ける（fresh 0.60 / prior 0.30）。`shortfall` を印字し、予算を下回ると incomplete になることを費用ゲートで言う |
| E39 | 所有者が ADR で受け入れた所見を帳簿に書く場所が無く、次走で再検証・再報告される | `findings.py accept --fingerprint --record --reason`（`dispositions.json`、追記のみ・`--withdraw` で反転）。`seed --prior` は受け入れ済みを `accepted_prior` に列挙し、引用元が不変なら再検証も再報告もしない（`record` が同じ主張を抑止）、変われば `prior_accepted_changed_source` で狩る |
| E40 | knowledge の 2026-11-09 の教訓 4 件がクラスに無い | agent-runtime.md: キャッシュのクラスに新しい出典と「名指しの拒否は第 2 線」、「承認ダイアログが呼び出しより少なく見せる」「レーンが書けるディレクトリを再開で再利用」を追加。generic.md の資源クラスに x/net/html の二次割り当て（2026-11-08）を出典追加。「所見を直す前に問う」は severity.md 規則 3 の出典 |

## 区切り (10) での採用（2026-11-09）

E37〜E40 を採用した（107 テスト緑）。E37: `schema.json` は 2 欄を任意にしておき（前回実行の
レコードを prior として読めるように）、`findings.py add` が新規 confirmed に必須として要求し、
規則 3 を機械で守る。brief の `required_fields` は 2 欄を列挙する。報告書は所見ごとに
「成立に要る行為／動作を決めた記録」を印字し、`documentation` ノートの節を持つ。
E38: `estimate` は `fresh_units`・`prior_units`・`shortfall` を返し、`candidates_per_unit`
は 2 値の表になった。E39: `dispositions.json` は findings.py が所有。報告書は所見の下に
「所有者の処置」を、次走の報告書は「所有者が受け入れた前回の所見」を列挙する。
E40: クラスは 54、出典 119 件を knowledge の実物で検査済み。
