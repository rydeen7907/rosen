"""
路線経路抽出プログラム 大阪メトロ版
ソース：東京メトロ版

2024.06.28いじり開始
環境：Python3.12
参考：https://qiita.com/galileo15640215/items/d7737d3e08c7bb3dba80
      https://www.ekidata.jp/

注1)：コスモスクエア＜＝＞住之江公園 運行会社は大阪メトロだが新交通システムのため対象外
注2)：いまざとライナーはBRT扱いにより対象外
注3)：他社線への乗入部分は対象外
注4)：複数の会社線には非対応 

"""

#必要なモジュール
import pandas as pd
import matplotlib.pyplot as plt
import japanize_matplotlib
import numpy as np
import networkx as nx

#csvファイルからpandsa形式のテーブルを作成
station = pd.read_csv("station20240426free.csv") # 駅データ
join = pd.read_csv("join20240426.csv") # 接続・乗換駅データ
pref = pd.read_csv("pref.csv") # 都道府県は省略可
line = pd.read_csv("line20240426free.csv") # 路線名データ
company = ("company20240328.csv") # 鉄道会社・路線データ

#例：全国の駅から大阪メトロの駅のみ抽出する 大阪メトロ...company_cd == 249
metro = station[["station_cd", "station_name", "line_cd", "lon", "lat"]]
metro = pd.merge(metro, line, on = 'line_cd')
metro = metro[metro["company_cd"] == 249]
metro = metro[["station_cd", "station_name", "line_cd", "lon_x", "lat_x", "line_name", "line_color_c", "line_color_t"]]
lon = metro["lon_x"]
lat = metro["lat_x"]
metro["lon"] = lon
metro["lat"] = lat
metro = metro[["station_cd", "station_name", "line_cd", "lon", "lat", "line_name"]]

#例：大阪メトロの接続辺を抽出する 路線...line_cd == 99618---99624, 99652
metro_join = join[(join["line_cd"]==99618)|(join["line_cd"]==99619)|(join["line_cd"]==99620)|(join["line_cd"]==99621)|(join["line_cd"]==99622)|(join["line_cd"]==99623)|(join["line_cd"]==99624)|(join["line_cd"]==99652)]
metro_join = metro_join[["station_cd1", "station_cd2"]]

#グラフの宣言
G = nx.Graph()
#頂点を駅名にする
G.add_nodes_from(metro["station_name"])
#plotの座標を設定
pos={}
for i, j, k in zip(metro["station_name"], metro["lon"], metro["lat"]):
  pos[i] = (j, k)
#リストeにstation_nameとstation_cdを格納し、リンクさせる
e = []
for i, j in zip(metro["station_name"], metro["station_cd"]):
  e.append([i, j])
#グラフに辺情報を加える
for i, j in zip(metro_join["station_cd1"], metro_join["station_cd2"]):
    for k in e:
      if k[1] == i:
        for l in e:
          if l[1] == j:
            G.add_edge(k[0], l[0])
#グラフの出力の設定
plt.figure(figsize=(10,10),dpi=200)
plt.title('大阪メトロ', fontsize=20)
plt.axes().set_aspect('equal', 'datalim')
nx.draw_networkx(G, pos, node_color='b', alpha=0.8, node_size=10, font_size=5, font_family='IPAexGothic')
plt.show()

#辺に重みとして駅間の距離を持たせるためのデータ作成
dist = []
cd1_lat = []
cd1_lon = []
cd2_lat = []
cd2_lon = []
not_exist = [] #joinテーブルには存在しているが、stationテーブルには存在していないstation_cdを格納
for i, j in zip(metro_join["station_cd1"], metro_join["station_cd2"]):
  flag = True
  for k, l, m in zip(metro["station_cd"], metro["lat"], metro["lon"]):
    if i == k:
      cd1_x = l
      cd1_y = m
      cd1_lat.append(l)
      cd1_lon.append(m)
      flag = False
    if j == k:
      cd2_x = l
      cd2_y = m
      cd2_lat.append(l)
      cd2_lon.append(m)
  if flag:
    not_exist.append([i, j])
    #print(i, j)
  else:
    dist.append(((cd1_x-cd2_x)**2 + (cd1_y-cd2_y)**2)**0.5)
#このまま実行するとエラー ValueError: Length of values does not match length of index
#どうやら"station_cd" == 2800701と2800702はstationテーブルに存在しておらず、joinテーブルから不要なので削除
#以下2行は...metro_join = metro_join[metro_join["station_cd1"] != 2800701]...と等価
for i in range(len(not_exist)):
  metro_join = metro_join[metro_join["station_cd1"] != not_exist[i][0]]
#joinテーブルに列を追加
metro_join["cd1_lat"] = cd1_lat
metro_join["cd1_lon"] = cd1_lon
metro_join["cd2_lat"] = cd2_lat
metro_join["cd2_lon"] = cd2_lon
metro_join["distance"] = dist

#nodes is station_name
#グラフに辺の重みを与える
for i, j, m in zip(metro_join["station_cd1"], metro_join["station_cd2"], metro_join["distance"]):
    for k in e:
      if k[1] == i:
        for l in e:
          if l[1] == j:
            G.add_edge(k[0], l[0], weight=m)

#nodes is station_cd
G = nx.Graph()
G.add_nodes_from(metro["station_cd"])
pos={}
for i, j, k in zip(metro["station_cd"], metro["lon"], metro["lat"]):
  pos[i] = (j, k)
for i, j, m in zip(metro_join["station_cd1"], metro_join["station_cd2"], metro_join["distance"]):
  G.add_edge(i, j, weight=m)
#station_cdを頂点にしたときに、同名のstation_nameでも路線ごとにstation_cdが設定されているため、このままでは他の路線との接続辺を持っていない
#そこで、重み0として同名の駅を接続させる
for i, j in zip(metro["station_name"], metro["station_cd"]):
  for k, l in zip(metro["station_name"], metro["station_cd"]):
    if i == k and j != l:
      G.add_edge(j, l, weight=0)

#スタートとゴールの駅を設定(鉄道会社共通)
st_name = "井高野"
go_name = "大日"
#station_nameからstation_cdを検索
for i, j in zip(metro["station_name"], metro["station_cd"]):
  if i == st_name:
    st = j
  if i == go_name:
    go = j
#最短経路を探索
dij = nx.dijkstra_path(G, st, go)
out = []
for k in range(len(dij)):
  for i, j in zip(metro["station_name"], metro["station_cd"]):
    if j == dij[k]:
      out.append(i)
print(out)

# 駅名をテキストファイルに書き込み
with open('route_osakametro.txt', 'w', encoding='utf-8') as f:
    for station_name in out:
        f.write(station_name + '\n')
        
#最短経路用のグラフを宣言
G_root = nx.Graph()
G_root.add_nodes_from(dij)
pos_root = {}
for l in dij:
  for i, j, k in zip(metro["station_cd"], metro["lon"], metro["lat"]):
    if l == i:
      pos_root[l] = (j, k)
for i in range(len(dij)-1):
  G_root.add_edge(dij[i], dij[i+1])

plt.figure(figsize=(10,10),dpi=200)
plt.title('大阪メトロ', fontsize=20)
plt.axes().set_aspect('equal', 'datalim')
nx.draw_networkx(G, pos, node_color='b', alpha=0.3, node_size=10, with_labels= False)
c = ['green' if n==st else 'red' if n!=go else'yellow' for n in G_root.nodes()]
n_size = [30 if n==st else 10 if n!=go else 30 for n in G_root.nodes()]
nx.draw_networkx(G_root, pos_root, node_color=c, alpha=0.9, node_size=n_size, with_labels= False)
plt.show()
