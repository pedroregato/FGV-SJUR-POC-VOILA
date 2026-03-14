import ijson

caminho = "F:/FGV-SJUR/resultado_arquivamento/json/dashboard_data.json"

with open(caminho, "r", encoding="utf-8") as f:
    parser = ijson.items(f, "item.publications.item")
    for i, pub in enumerate(parser):
        print(pub.get("html_content")[:200])  # mostra só o início
        if i >= 5:  # só as 5 primeiras publicações
            break
