# Agricultural Land Pin Tools

## 概要
  
本リポジトリで提供しているArcGIS Pro 用のサンプル Python ツールボックス には、次の2つのツールが含まれています。

* WAGRI運営事務局が提供している農地APIの「[農地ピン情報取得API：SearchByCityCode](https://wagri.naro.go.jp/wagri_api/agriculturalland-searchbycitycode/)」を利用して、指定した市区町村の農地ピン情報をGeojson 形式のファイルとしてダウンロードするツール
* Geojson 形式のファイルをArcGIS のフィーチャクラスにインポートするツール

なお、農地ピン情報をGeojson 形式のファイルでダウンロードの前に、

* 農地ピン情報取得API の利用のために、WAGRI運営事務局からid, secret 情報を入手後、xxxx.ini ファイル への書き込み
* 市区町村指定用のｘｘｘ.csv の準備が必要です



## サンプル Python ツールボックス

## 免責事項
* 本リポジトリに含まれるノートブック ファイルはサンプルとして提供しているものであり、動作に関する保証、および製品ライフサイクルに従った Esri 製品サポート サービスは提供しておりません。
* 本ツールに含まれるツールによって生じた損失及び損害等について、一切の責任を負いかねますのでご了承ください。
* 弊社で提供しているEsri 製品サポートサービスでは、本ツールに関しての Ｑ＆Ａ サポートの受付を行っておりませんので、予めご了承の上、ご利用ください。詳細は[
ESRIジャパン GitHub アカウントにおけるオープンソースへの貢献について](https://github.com/EsriJapan/contributing)をご参照ください。

## ライセンス
Copyright 2023 Esri Japan Corporation.

Apache License Version 2.0（「本ライセンス」）に基づいてライセンスされます。あなたがこのファイルを使用するためには、本ライセンスに従わなければなりません。
本ライセンスのコピーは下記の場所から入手できます。

> http://www.apache.org/licenses/LICENSE-2.0

適用される法律または書面での同意によって命じられない限り、本ライセンスに基づいて頒布されるソフトウェアは、明示黙示を問わず、いかなる保証も条件もなしに「現状のまま」頒布されます。本ライセンスでの権利と制限を規定した文言については、本ライセンスを参照してください。

ライセンスのコピーは本リポジトリの[ライセンス ファイル](./LICENSE)で利用可能です。
