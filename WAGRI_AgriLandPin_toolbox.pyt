# -*- coding: utf-8 -*-
"""
Name        : WAGRI_AgriLandPin_toolbox.pyt
Purpose     : WAGRI API SearchByCityCode で農地ピンをGeoJSON としての取得、フィーチャクラスへの変換、
              フィーチャクラスにフィールド エイリアスを設定する3つのジオプロセシング ツールが入った Python toolbox です。
Author      :
Copyright   :
Created     :2023/08/24
Last Updated:
ArcGIS Version: ArcGIS Pro 2.9 以上
"""
import arcpy
import os
import configparser
import json
import requests
import time
import pandas as pd
import chardet # 文字コード判定のために追加
from pathlib import Path
from urllib.parse import urljoin
from dataclasses import dataclass

#
# WAGRI API を使う処理をクラス
#
@dataclass(frozen=True)
class WagriAPIServices():
    """
    WAGRIのToken, APIのURLの定義
    @dataclass(frozen=True)で readonly のクラスに変更
    """
    HOST = 'https://api.wagri.net'
    TOKEN = '/Token'
    SEARCH_BY_CITYCODE = '/API/Public/AgriculturalLand/SearchByCityCode'
    GET_STATUS = '/API/AsyncApi/GetStatus'
    GET_RESULT = '/API/AsyncApi/GetResult'
    def __init__(self):
        return
    def __del__(self):
        return
    def get_token_url(self):
        """
        https://api.wagri.net/Token
        """
        return urljoin(WagriAPIServices.HOST, WagriAPIServices.TOKEN)

    def get_status_url(self):
        """
        https://api.wagri.net/API/AsyncApi/GetStatus
        """
        return urljoin(WagriAPIServices.HOST, WagriAPIServices.GET_STATUS)

    def get_result_url(self):
        """
        https://api.wagri.net/API/AsyncApi/GetResult
        """
        return urljoin(WagriAPIServices.HOST, WagriAPIServices.GET_RESULT)
  
    def get_search_by_code_url(self):
        """
        https://api.wagri.net/API/Public/AgriculturalLand/SearchByCityCode
        """
        return urljoin(WagriAPIServices.HOST, WagriAPIServices.SEARCH_BY_CITYCODE)

class WagriAPISearchByCityCode():
    """
    WAGRI API SearchByCityCode を利用してGeoJSONのデータを取得するクラス
    """
    def __init__(self):
        """
        cliend_id, client_secret を記載したiniファイルはconf フォルダー下に格納
          conf
            |- wagri_config.ini
        """
        # ini ファイルを読み込み
        config_ini = configparser.ConfigParser()
        self.conf_file = self.__get_config_file()
        config_ini.read(self.conf_file, encoding='utf-8')
        # WAGRI のcliend_id, client_secret を読み込み
        self.client_id = config_ini.get('WAGRI', 'id')
        self.client_secret = config_ini.get('WAGRI', 'secret')
        # WagriAPIServices のクラスインスタンス
        self.WagriServices = WagriAPIServices()
        return
    def __del__(self):
        return
    
    # 関数定義
    # private：def __func():
    def __get_config_file(self):
        """wagri_config.ini を取得"""
        folder = os.path.dirname(__file__) #pyt が格納されているフォルダー
        config_folder = os.path.join(folder, "conf") # conf フォルダのディレクトリ
        return os.path.join(config_folder, "wagri_config.ini")
        
    def __get_token(self, client_id, client_secret):
        """
        token をjson で取得
        """
        url = self.WagriServices.get_token_url()
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        payload = {'grant_type': 'client_credentials',
                   'client_id': client_id ,
                   'client_secret': client_secret}
        response = requests.post(url, payload)
        # response.json() = {'access_token': '', 'token_type': 'bearer', 'expires_in':  }
        return response.json()
    
    def __savefile_result(self, response, file_name):
        """
        response.text をgeojson ファイルとして保存
        """
        ret = ""
        with open(file_name, mode='w', encoding='utf-8') as savefile:
            savefile.write(response.text)
            ret = file_name
        return {"result": "OK" , "file_name": ret }

    def __savefile_sync_result(self, token, request_id, file_name):
        """
        GetResult APIにリクエストし、非同期実行で処理した結果を取得
        """
        url = self.WagriServices.get_result_url()
        payload = {"RequestId": request_id}
        headers = {'X-Authorization': token,
                   'Accept':'application/geo+json',
                   'X-IsGeoJson': 'True'}
        response = requests.get(url, headers=headers, params=payload)
        result_json = self.__savefile_result(response, file_name)
        return result_json

    def __get_geojson(self, token, request_id, file_name):
        """
        GetStatus APIにリクエストし、非同期実行のステータスを取得
        """
        url = self.WagriServices.get_status_url()
        payload = {"RequestId": request_id}
        headers = {'X-Authorization': token}
        response = requests.get(url, headers=headers, params=payload)
        # print(response.text) 
        #{"RequestId":"xxx","Status":"End","RequestDate":"2023-08-06T15:xx","EndDate":"2023-08-06T15:xx"}
        arcpy.AddMessage(u"    {}".format(response.text))
        # 辞書のキーと値の組み合わせの存在を確認: in演算子, items()
        # https://note.nkmk.me/python-dict-in-values-items/
        if (('Status', 'End') in response.json().items()):
            print('Finished: %s' % response.json()['EndDate'])
            result_json = self.__savefile_sync_result(token, request_id, file_name)
            return result_json
        else: # sleep 後に再度ステータスをチェック
            time.sleep(2)
            # print('Continue.... ')
            arcpy.AddMessage(u"    {}".format('Continue.... '))
            return self.__get_geojson(token, request_id, file_name)

    # 関数定義
    # public：def func():
    def get_agriculturalland_geojson(self, city_code, file_name, is_async = True):
        """
        SearchByCityCode で農地ピンをGeoJSONで取得
        """
        # tokenを取得
        token_json = self.__get_token(self.client_id, self.client_secret)
        if token_json.get("access_token") is None:
            return {"result": "Token取得に失敗しました"}
        token = token_json['access_token']
        IsAsync = "" #'X-IsAsync'へ指定するのは文字列のようなので変換
        if is_async:
            IsAsync = 'True'
        else:
            IsAsync = 'False'
        
        url = self.WagriServices.get_search_by_code_url()
        headers = {'X-Authorization': token,
                   'X-IsAsync': IsAsync,
                   'Accept': 'application/geo+json',
                   'X-IsGeoJson': 'true'}
        payload = {"CityCode": city_code}
        response = requests.get(url, headers=headers, params=payload)
        result_json = ""
        if is_async: # 非同期での呼び出しはStatusをチェックして処理が完了したらファイルへ保存
            request_id = response.json() # {'RequestId': ' '}
            result_json = self.__get_geojson(token, request_id['RequestId'] , file_name)
        else: # 同期での呼び出しは結果をすぐにファイルへ保存
            result_json = self.__savefile_result(response, file_name)
        return result_json

# 
# 2023年8月現在JSONToFeatures を使って変換した時に PointZ のジオメトリになってしまうようなので、それを回避するArcPy を使った自前の変換クラス
# 
# - GistにあったGeoJSON からFeatureClass へArcPyで変換する方法を参考にしながら実装
#   https://gist.github.com/d-wasserman/070ec800584d18a22e1b5a636ca183b7
# 
class GeojsonToFeaturesEx():
    def __init__(self):
        return
    def __del__(self):
        return

    def __write_geojson_to_records(self, jsonfile):
        #gjson_data = json.load(jsonfile, encoding='utf-8')
        #日本語が属性に入っている場合にcp932 のエラーになるので、encoding を判別して読込するように変更
        gjson_data= []
        with open(jsonfile, 'rb') as fb:
            chardic = []
            b = fb.read()
            chardic = chardet.detect(b)
            with open(jsonfile, 'r', encoding=chardic['encoding']) as fp:
                gjson_data = json.loads(fp.read())
        
        records = []
        for feature in gjson_data["features"]:
            try:
                row = {}
                row["geometry"] = feature["geometry"]
                row["type"] = feature["geometry"]["type"]
                feat_dict = feature["properties"]
                for prop in feat_dict:
                    row[prop] = feat_dict[prop]
                records.append(row)
            except:
                pass
        return records
        
    def geojson_to_features(self, jsonfile, output_fc, projection=arcpy.SpatialReference(4326)):

        blResult = True
    
        try:
            path = os.path.split(output_fc)[0]
            name = os.path.split(output_fc)[1]
            
            arcpy.AddMessage(u"{0} への 変換を開始します".format(name))
            arcpy.AddMessage(u"    GeoJSON のレコード読込み中...")
            records = self.__write_geojson_to_records(jsonfile)

            type = records[0]["type"]
            arctype = None
            if type == "FeatureCollection":
                arcpy.AddWarning(u"FeatureCollections は、 point,line, polygon のいずれかに分解されます")
                arctype = "POINT" 
            elif type == "LineString":
                arctype = "POLYLINE" 
            else:
                arctype = str(type).upper()
            arcpy.AddMessage(u"    フィーチャクラス の新規作成...")
            arcpy.CreateFeatureclass_management(path, name, arctype, spatial_reference=projection)
            
            record_dict = records[0]
            for key in record_dict:
                if key == "geometry":
                    continue
                if key == "type":
                    continue
                element = record_dict[key]
                field_type = "TEXT"
                #今回はTEXTのみなのでコメントアウト
                #try:
                #    num_element = float(element)
                #    if isinstance(num_element, float):
                #        field_type = "DOUBLE" 
                #    if isinstance(element, int):
                #        field_type = "LONG" 
                #except:
                #    pass
                arcpy.AddField_management(output_fc, arcpy.ValidateFieldName(key, path), field_type)
            field_list = [f.name for f in arcpy.ListFields((output_fc)) if f.type not in ["OID", "Geometry"]
                              and f.name.lower() not in ["shape_area", "shape_length"]]
            fields = ["SHAPE@"] + field_list
            arcpy.AddMessage(u"    フィーチャクラス にレコードを書き込み中...")
            with arcpy.da.InsertCursor(output_fc, fields) as icursor:
                for record in records:
                    new_row = []
                    for field in fields:
                        if field == "SHAPE@":
                            try:
                                geom = arcpy.AsShape(record.setdefault("geometry", None))
                            except:
                                geom = None
                            new_row.append(geom)
                        else:
                            new_row.append(record.setdefault(str(field), None))
                    icursor.insertRow(new_row)

            arcpy.AddMessage(u"{0} への 変換完了".format(name))
        except arcpy.ExecuteError:
            arcpy.AddError(arcpy.GetMessages(2))
            blResult = False
        except Exception as e:
            arcpy.AddError(e.args[0])
            blResult = False
    
        return blResult


#
# 市区町村5桁コードから6桁の検査数値コードありのコードに変換する関数
#  - 参考1) 全国地方公共団体コードにおける「検査数字」について（情報提供：総務省）
#    方式（モジュラス11）
#    https://www.j-lis.go.jp/spd/code-address/cms_1750514.html#cd
#  - 参考2) modulus11 python code 
#    https://github.com/PetrDlouhy/python-modulus11/blob/master/src/modulus11/mod11.py
# 
def cal_modulus11(city_code, factors = "65432"):
    #print(citycode) # 5桁コードか確認用
    #6.5.4.3.2を乗じて算出した積の和を計算
    sum = 0
    for (f,n) in zip(factors, city_code):
        sum += int(f)*int(n)
    #余りを計算し、注に書いている余りが0,1,10の時の処理
    chk =  sum % 11
    if chk == 0:
        return '{city_code}'.format(city_code=city_code) + '{arg1}'.format(arg1=1)
    if chk == 1:
        return '{city_code}'.format(city_code=city_code) + '{arg0}'.format(arg0=0)
    if chk == 10:
        return '{city_code}'.format(city_code=city_code) + '{arg1}'.format(arg1=1)
    return '{city_code}'.format(city_code=city_code) + '{}'.format(11-chk)

# 
# ジオプロセシング ツールボックスの定義
# - テンプレート
#   https://pro.arcgis.com/ja/pro-app/latest/arcpy/geoprocessing_and_python/a-template-for-python-toolboxes.htm
#
class Toolbox(object):
    def __init__(self):
        """ツールボックスを定義する（ツールボックスの名前は .pytファイルの名前である)。"""
        self.label = "WAGRI 農地ピン 処理用ツールボックス"
        self.alias = ""

        # このツールボックスに関連するツールクラスのリスト
        self.tools = [Wagri_GetAgriLandPin, GeoJsonToFc, BatchAlterFieldAlias]

# 
# 各ジオプロセシング ツールの定義
# 
class Wagri_GetAgriLandPin(object):
    def __init__(self):
        """ツールを定義する（ツール名はクラス名）。"""
        self.label = "01_農地ピン-GeoJSON を WAGRI API で取得ツール"
        self.description = "WAGRI の農地ピン情報取得API：SearchByCityCodeAPI を使って、指定した自治体の農地ピンを GeoJSON 形式のファイルとして取得するツールです"
        self.canRunInBackground = False

    def __get_city_csv_file(self):
        """city_code.csv を取得"""
        folder = os.path.dirname(__file__) #pyt が格納されているフォルダー
        config_folder = os.path.join(folder, "conf") # conf フォルダのディレクトリ
        return os.path.join(config_folder, "city_code.csv")

    def getParameterInfo(self):
        """ツールの実行に必要なパラメーターの設定"""
        #param0 市区町村の選択 (複数選択可)
        #param1 GeoJSON を出力するフォルダー

        param0 = arcpy.Parameter(
            displayName="農地ピンを取得する市区町村の選択 (複数選択可)",
            name="city_code",
            datatype="GPString",
            parameterType="Required",
            direction="Input",
            multiValue=True)
        
        param0.filter.type = "Value List"
        #city_code.csv を読み込み、filter.list に設定
        csv = self.__get_city_csv_file()
        df = pd.read_csv(csv, header=0)
        #パラメーター用の列を用意して、<市区町村コード>_<市区町村名>を格納
        df['param'] = df['code'].astype(str) + "_" + df['name']
        # modulus11 実行時に空白があるとエラーになるので、空白を削除する
        df['param'] = df['param'].str.replace(' ', '')
        df['param'] = df['param'].str.replace('　', '')

        param_list = df['param'].to_list()
        param0.filter.list = param_list
        
        param1 = arcpy.Parameter(
            displayName="農地ピンGeoJSON を出力するフォルダー",
            name="folder",
            datatype="DEFolder",
            parameterType="Required",
            direction="Input",
            multiValue=False)
        
        params = [param0, param1]
        return params

    def isLicensed(self):
        """ライセンスチェックの設定"""
        return True

    def updateParameters(self, parameters):
        """パラメーターの検証と更新設定。内部検証が実行される前に、パラメータの値とプロパティを変更します。 このメソッドは、パラメータが変更されるたびに呼び出されます。"""
        return

    def updateMessages(self, parameters):
        """パラメーターの検証と検証のメッセージ設定。各ツールの内部検証で作成されたメッセージを修正する。 パラメータを修正する。 このメソッドは内部バリデーションの後に呼び出される。"""
        return

    def execute(self, parameters, messages):
        """実行時に処理を行うスクリプト。ツールのソースコード。"""
        city_code_arcgis = parameters[0].valueAsText
        folder = parameters[1].valueAsText

        # ArcGIS で複数値を入力すると ";" で区切られるため、スプリットしてリスト化
        city_code5_list = city_code_arcgis.split(';')
        # クラスの初期化
        wagri = WagriAPISearchByCityCode()
        for city_code5 in city_code5_list:
            try:
                city_code6 = cal_modulus11(city_code5[:5]) #パラメーターから5桁数字だけ抽出
                file_name = "AgriLandPin_%s.geojson" % (city_code5)
                save_file = os.path.join(folder, file_name)
                if os.path.isfile(save_file):
                    arcpy.AddWarning(f'{save_file} がすでに存在するため取得をスキップします。')
                else:
                    arcpy.AddMessage(f'{city_code5} の農地ピンの取得中...')
                    req = wagri.get_agriculturalland_geojson(city_code6, save_file, True) # 非同期APIでの処理
                    # print(req)
                    arcpy.AddMessage(f'{save_file} へ保存しました。')
                arcpy.AddMessage(u"\u200B") #改行
            except:
                arcpy.AddError(f'{city_code5} は5桁の数値ではありません。city_code.csv の name 列には5桁の市区町村コードを入力してください。')
                pass
        # 後始末
        del wagri

    def postExecute(self, parameters):
        """ツールの処理が完了した後の設定。このメソッドは、出力が処理されて表示に追加された後に実行されます。"""
        return

class GeoJsonToFc(object):
    def __init__(self):
        """ツールを定義する（ツール名はクラス名）。"""
        self.label = "02_農地ピン-GeoJSON → フィーチャ 変換ツール"
        self.description = "農地ピンの GeoJSON をフィーチャクラスに変換するツールです"
        self.canRunInBackground = False

    def getParameterInfo(self):
        """ツールの実行に必要なパラメーターの設定"""
        #param0 GeoJSON の選択 (複数選択可)
        #param1 Out workspace (File Geodatabase)
        param0 = arcpy.Parameter(
            displayName="農地ピンGeoJSON の選択 (複数選択可)",
            name="geojson",
            datatype="DEFile",
            parameterType="Required",
            direction="Input",
            multiValue=True)
        param0.filter.list = ['geojson']
        
        param1 = arcpy.Parameter(
            displayName="農地ピン フィーチャクラスを保存する 出力ワークスペース",
            name="out_workspace",
            datatype="DEWorkspace",
            parameterType="Required",
            direction="Input")
        param1.filter.list = ["Local Database"]
        
        params = [param0, param1]
        return params

    def isLicensed(self):
        """ライセンスチェックの設定"""
        return True

    def updateParameters(self, parameters):
        """パラメーターの検証と更新設定。内部検証が実行される前に、パラメータの値とプロパティを変更します。 このメソッドは、パラメータが変更されるたびに呼び出されます。"""
        return

    def updateMessages(self, parameters):
        """パラメーターの検証と検証のメッセージ設定。各ツールの内部検証で作成されたメッセージを修正する。 パラメータを修正する。 このメソッドは内部バリデーションの後に呼び出される。"""
        return

    def execute(self, parameters, messages):
        """実行時に処理を行うスクリプト。ツールのソースコード。"""
        geojson_file_raw = parameters[0].valueAsText
        ws = parameters[1].valueAsText

        # ArcGIS で複数値を入力すると ";" で区切られるため、スプリットしてリスト化
        geojson_file_list = geojson_file_raw.split(';') 

        #入力された GeoJSON ファイルからフィーチャ クラスに変換
        convGeojson = GeojsonToFeaturesEx()
        for geojson_file in geojson_file_list:
            try:
                name = os.path.splitext(os.path.basename(geojson_file))[0] #パスからファイル名を取得
                #arcpy.conversion.JSONToFeatures(
                #    in_json_file = geojson_file,
                #    out_features = name,
                #    geometry_type = "POINT"
                #)
                #arcpy.AddMessage(f'{name[12:]} の変換完了')
                #自前の変換ツールでフィーチャクラスへ変換
                output_fc = os.path.join(ws, name)
                if arcpy.Exists(output_fc):
                    arcpy.AddWarning(f'{name} がすでに存在するため変換をスキップします。')
                else:
                    convGeojson.geojson_to_features(geojson_file, output_fc)
                arcpy.AddMessage(u"\u200B") #改行

            # 空っぽの geojson ファイル (1kb) はエラーが出るので、スキップして続行
            except Exception as e:
                arcpy.AddError(e.args[0])
                #arcpy.AddMessage(f'{name[12:]} は農地ピンが存在しません')
                arcpy.AddMessage(u"\u200B") #改行
                pass
        
        #後始末
        del convGeojson

    def postExecute(self, parameters):
        """ツールの処理が完了した後の設定。このメソッドは、出力が処理されて表示に追加された後に実行されます。"""
        return


class BatchAlterFieldAlias(object):
    def __init__(self):
        """ツールを定義する（ツール名はクラス名）。"""
        self.label = "03_農地ピン-フィーチャクラスにフィールド エイリアス名 設定ツール"
        self.description = "農地ピンのフィーチャクラスにフィールド エイリアス名を設定するツールです"
        self.canRunInBackground = False

    def __get_pin_fields_file(self):
        """agri_land_pin_fields.txt を取得"""
        folder = os.path.dirname(__file__) #pyt が格納されているフォルダー
        config_folder = os.path.join(folder, "conf") # conf フォルダのディレクトリ
        return os.path.join(config_folder, "agri_land_pin_fields.txt")
        
    def getParameterInfo(self):
        """ツールの実行に必要なパラメーターの設定"""
        #param0 FeatureClass (複数選択可)
        param0 = arcpy.Parameter(
            displayName="農地ピンのフィーチャクラス (複数選択可)",
            name="agri_land_pin",
            datatype="DEFeatureClass",
            parameterType="Required",
            direction="Input",
            multiValue=True)

        params = [param0]
        return params

    def isLicensed(self):
        """ライセンスチェックの設定"""
        return True

    def updateParameters(self, parameters):
        """パラメーターの検証と更新設定。内部検証が実行される前に、パラメータの値とプロパティを変更します。 このメソッドは、パラメータが変更されるたびに呼び出されます。"""
        return

    def updateMessages(self, parameters):
        """パラメーターの検証と検証のメッセージ設定。各ツールの内部検証で作成されたメッセージを修正する。 パラメータを修正する。 このメソッドは内部バリデーションの後に呼び出される。"""
        return

    def execute(self, parameters, messages):
        """実行時に処理を行うスクリプト。ツールのソースコード。"""
        fc_raw = parameters[0].valueAsText

        # ArcGIS で複数値を入力すると ";" で区切られるため、スプリットしてリスト化
        fc_list = fc_raw.split(';')
        
        # 設定ファイルからフィールド名、エイリアス名を読み込み
        fields_file = self.__get_pin_fields_file()
        fieldsParams = []
        with open(fields_file, encoding='utf-8') as f:
            next(f) # ヘッダーは読み飛ばす
            for line in f:
                line = line.rstrip("\n")
                params = line.split(";")
                fieldsParams.append(params)
        
        # 各フィーチャクラスにエイリアス名を設定する
        for fc in fc_list:
            fc_name = os.path.basename(fc)
            arcpy.AddMessage(f'{fc_name} にフィールド エイリアス名を設定中...')
            for p in fieldsParams:
                field_name = p[0]
                alias_name = p[1]
                arcpy.AddMessage(f'    フィールド:{field_name} に エイリアス名:{alias_name} を設定')
                arcpy.management.AlterField(fc, field=field_name, new_field_alias=alias_name)
            arcpy.AddMessage(f'{fc_name} にフィールド エイリアス名を設定完了しました。')
            arcpy.AddMessage(u"\u200B") #改行
        return

    def postExecute(self, parameters):
        """ツールの処理が完了した後の設定。このメソッドは、出力が処理されて表示に追加された後に実行されます。"""
        return



