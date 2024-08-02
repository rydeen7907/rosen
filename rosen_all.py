"""
路線経路抽出プログラム 全国全路線版
ソース：東京メトロ版

2024.06.28いじり開始
環境：Python3.12
参考：https://qiita.com/galileo15640215/items/d7737d3e08c7bb3dba80
      https://www.ekidata.jp/ (データダウンロード元 要会員登録)

注1)：ダイクストラ法に基づいた経路で検索
      他路線接続駅経由であってもアルゴリズムに載っていなければエラーとなり停止する
注2)：路線データなどのデータ量が大きいため入力までに時間を要する
注3)：
注4)：
"""

import pandas as pd
import matplotlib.pyplot as plt
import japanize_matplotlib
import numpy as np
import networkx as nx


def load_data():
    """データの読み込み"""
    station = pd.read_csv("station20240426free.csv")
    join = pd.read_csv("join20240426.csv")
    line = pd.read_csv("line20240426free.csv", usecols=["line_cd", "line_name"])

    # 必要な情報にマージ
    zen = station[["station_cd", "station_name", "line_cd", "lon", "lat"]]
    zen = pd.merge(zen, line, on='line_cd', how='left')[["station_cd", "station_name", "line_cd", "lon", "lat", "line_name"]]

    return zen, join

def calculate_distances(zen, join):
    """駅間の距離計算"""

    def get_coordinates(station_cd, zen):
        """緯度経度を取得"""
        row = zen[zen["station_cd"] == station_cd]
        if row.empty:
            return None, None
        return row["lat"].values[0], row["lon"].values[0]

    distances = []
    not_exist = []

    for cd1, cd2 in zip(join["station_cd1"], join["station_cd2"]):
        lat1, lon1 = get_coordinates(cd1, zen)
        lat2, lon2 = get_coordinates(cd2, zen)
        if lat1 is None or lat2 is None:
            not_exist.append((cd1, cd2))
            continue
        distance = ((lat1 - lat2) ** 2 + (lon1 - lon2) ** 2) ** 0.5
        distances.append((cd1, cd2, lat1, lon1, lat2, lon2, distance))

    # DataFrame に変換し、存在しない駅を削除
    dist_df = pd.DataFrame(distances, columns=["station_cd1", "station_cd2", "cd1_lat", "cd1_lon", "cd2_lat", "cd2_lon", "distance"])
    for cd1, cd2 in not_exist:
        join = join[~((join["station_cd1"] == cd1) & (join["station_cd2"] == cd2))]

    join = pd.merge(join, dist_df[['station_cd1', 'station_cd2', 'distance']], on=['station_cd1', 'station_cd2'])

    return join

def create_graph(zen, join):
    """グラフを作成"""
    G = nx.Graph()
    G.add_nodes_from(zen["station_cd"])
    pos = {cd: (lon, lat) for cd, lon, lat in zip(zen["station_cd"], zen["lon"], zen["lat"])}

    for cd1, cd2, dist in zip(join["station_cd1"], join["station_cd2"], join["distance"]):
        G.add_edge(cd1, cd2, weight=dist)

    for name1, cd1, lat1 in zip(zen["station_name"], zen["station_cd"], zen["lat"]):
        for name2, cd2, lat2 in zip(zen["station_name"], zen["station_cd"], zen["lat"]):
            if name1 == name2 and cd1 != cd2 and lat1 == lat2:
                G.add_edge(cd1, cd2, weight=0)

    return G, pos

def input_station_info(station_data):
    """駅名の入力と該当する駅コードを取得"""
    while True:
        station_name = input("駅名を入力してください：")
        candidates = station_data[station_data["station_name"] == station_name]

        if len(candidates) > 1:
            print(f"{station_name} には複数の駅が存在します。")
            print(candidates[["station_name", "line_name"]]) 
            line_or_pref = input("路線名を入力してください：")
            candidates = candidates[candidates["line_name"] == line_or_pref]
        
        if len(candidates) == 1:
            return candidates["station_cd"].values[0]
        elif len(candidates) == 0:
            print("入力に誤りがあります。存在しない駅名か路線名です。もう一度入力してください。")
        else:
            print("入力に誤りがあります。もう一度入力してください。")

def find_shortest_path(G, start, goal, zen):
    """最短経路を探索し、結果を出力"""
    try:
        dij = nx.dijkstra_path(G, start, goal)
        out = [zen[zen["station_cd"] == cd]["station_name"].values[0] for cd in dij]
        print(out)

        with open("station_route_zenkoku.txt", 'w', encoding='utf-8') as f:
            for station_name in out:
                f.write(station_name + '\n')

        return dij
    except nx.NetworkXNoPath:
        print(f"出発駅コード {start} から到着駅コード {goal} への経路が見つかりませんでした。")
        return None

# 経路をグラフしたい時に解除
# ※  描画はカスタマイズが必要

#def plot_graph(G, pos, dij, zen):  # グラフ描画関数を削除
#    """グラフの描画"""
#    G_root = nx.Graph()
#    G_root.add_nodes_from(dij)
#    pos_root = {cd: pos[cd] for cd in dij}
#
#    for i in range(len(dij) - 1):
#        G_root.add_edge(dij[i], dij[i + 1])
#
#    plt.figure(figsize=(10, 10), dpi=200)
#    plt.title('全国全路線', fontsize=20)
#    plt.gca().set_aspect('equal', 'datalim')
#    nx.draw(G, pos, alpha=0.3, node_size=10, with_labels=False)
#    nx.draw(G_root, pos_root, edge_color='r', alpha=1.0, node_size=10, with_labels=False)
#    plt.show()

def main():
    # データの読み込み
    zen, join = load_data()
    
    # 駅間の距離計算
    join = calculate_distances(zen, join)
    
    # グラフの作成
    G, pos = create_graph(zen, join)
    
    # 駅名入力と最短経路探索
    while True:
        start_station = input_station_info(zen)
        goal_station = input_station_info(zen)
        if start_station != goal_station:
            break
        else:
            print("出発駅と到着駅が同じです。もう一度入力してください。")
    
    dij = find_shortest_path(G, start_station, goal_station, zen)
    if dij is not None:
        print("経路が見つかりました。")
    else:
        print("経路が見つからなかったため、プログラムを終了します。")

    # グラフの描画  # 描画部分を削除
    #plot_graph(G, pos, dij, zen)

if __name__ == "__main__":
    main()