from fastmcp import FastMCP
import requests
from collections import OrderedDict

mcp = FastMCP("riot-mcp-http")
api_key = 'RGAPI-788e7cc5-2d03-45ee-830a-82c0c79c47e7'
requesturl_items = "https://ddragon.leagueoflegends.com/cdn/16.1.1/data/ko_KR/item.json"
requesturl_champions = "https://ddragon.leagueoflegends.com/cdn/16.1.1/data/ko_KR/champion.json"
requesturl_summoners = "https://ddragon.leagueoflegends.com/cdn/16.1.1/data/ko_KR/summoner.json"

@mcp.tool
def get_puuid(user_name: str, user_tag: str) -> str:
    """Get puuid from Riot API using username and tag"""
    requesturl = "https://asia.api.riotgames.com/riot/account/v1/accounts/by-riot-id/"+user_name+"/"+user_tag+"?api_key="+api_key
    r = requests.get(requesturl)
    
    if r.status_code == 200:
        return r.json()['puuid']
    else:
        return f"Error: {r.status_code}"

@mcp.tool
def recent_matches(puuid: str, game_type: str, game_count: int) -> list:
    """Get recent match IDs from Riot API using puuid"""
    requesturl = "https://asia.api.riotgames.com/lol/match/v5/matches/by-puuid/"+puuid+"/ids?type="+game_type+"&start=0&count="+str(game_count)+"&api_key="+api_key
    r = requests.get(requesturl)

    return r.json()

@mcp.tool
def match_win_rate(puuid: str, game_type: str, game_count: int) -> dict:
    """Get match win rate from Riot API using puuid"""
    requesturl = "https://asia.api.riotgames.com/lol/match/v5/matches/by-puuid/"+puuid+"/ids?type="+game_type+"&start=0&count="+str(game_count)+"&api_key="+api_key
    r = requests.get(requesturl)

    # 승리 횟수
    win_count = 0

    for i in range(len(r.json())):
        match_requesturl = "https://asia.api.riotgames.com/lol/match/v5/matches/"+r.json()[i]+"?api_key="+api_key
        match_r = requests.get(match_requesturl)

        # 몇번째 참가자인지 확인
        participant_index = 0
        for j in range(10):
            if (match_r.json()['info']['participants'][j]['puuid']) == puuid:
                participant_index = j
                break

        if match_r.json()['info']['participants'][participant_index]['win']:
            win_count += 1

    match_win_rate = OrderedDict()
    match_win_rate["total_matches"] = len(r.json())
    match_win_rate["win_count"] = win_count
    match_win_rate["win_rate_percentage"] = round((win_count/len(r.json()))*100, 2)

    return match_win_rate

@mcp.tool
def match_result(match_id: str, puuid: str) -> dict:
    """Get match result from Riot API using match ID and puuid"""
    try:
        requesturl = "https://asia.api.riotgames.com/lol/match/v5/matches/"+match_id+"?api_key="+api_key
        r = requests.get(requesturl)
        r_items = requests.get(requesturl_items)
        r_champions = requests.get(requesturl_champions)
        r_summoners = requests.get(requesturl_summoners)

        if r.status_code != 200:
            return {"error": f"Match not found: {r.status_code}"}

        match_data = r.json()
        
        # 몇번째 참가자인지 확인
        participant_index = -1
        for i in range(len(match_data['info']['participants'])):
            if match_data['info']['participants'][i]['puuid'] == puuid:
                participant_index = i
                break
        
        if participant_index == -1:
            return {"error": "Participant not found in match"}

        participant = match_data['info']['participants'][participant_index]

        # 챔피언 한글 이름
        champion_name = participant['championName']
        champion_name_ko = r_champions.json()['data'].get(champion_name, {}).get('name', champion_name)

        # 소환사 스펠 한글 이름
        summoner1_id = participant['summoner1Id']
        summoner2_id = participant['summoner2Id']
        summoner1_name_ko = ""
        summoner2_name_ko = ""
        for key in r_summoners.json()['data'].keys():
            if r_summoners.json()['data'][key]['key'] == str(summoner1_id):
                summoner1_name_ko = r_summoners.json()['data'][key]['name']
            if r_summoners.json()['data'][key]['key'] == str(summoner2_id):
                summoner2_name_ko = r_summoners.json()['data'][key]['name']

        # 아이템 한글 이름
        item_names_ko = []
        ward_name_ko = ""
        for i in range(7):
            item_id = str(participant.get('item'+str(i), '0'))
            if i < 6:
                if item_id != '0' and item_id in r_items.json()['data']:
                    item_name_ko = r_items.json()['data'][item_id].get('name', item_id)
                    item_names_ko.append(item_name_ko)
            else:
                if item_id != '0' and item_id in r_items.json()['data']:
                    ward_name_ko = r_items.json()['data'][item_id].get('name', item_id)

        match_result = OrderedDict()
        match_result["game_mode"] = match_data['info'].get('gameMode', 'Unknown')
        match_result["game_duration_minutes"] = match_data['info']['gameDuration']//60
        match_result["game_duration_seconds"] = match_data['info']['gameDuration']%60
        match_result["match_id"] = match_data['metadata']['matchId']
        match_result["summoner_name"] = participant.get('riotIdGameName', '') + "#" + participant.get('riotIdTagline', '')
        match_result["champion"] = champion_name_ko
        match_result["champion_level"] = participant['champLevel']
        match_result["kills"] = participant['kills']
        match_result["deaths"] = participant['deaths']
        match_result["assists"] = participant['assists']
        match_result["gold_earned"] = participant['goldEarned']
        match_result["items"] = item_names_ko
        match_result["ward"] = ward_name_ko
        match_result["spells"] = summoner1_name_ko + "(D), " + summoner2_name_ko + "(F)"
        
        team_id = 0 if participant['teamId'] == 100 else 1
        team_kills = match_data['info']['teams'][team_id]['objectives']['champion']['kills']
        if team_kills > 0:
            match_result["kill_participation_rate"] = round((participant['kills'] + participant['assists']) / team_kills, 2)
        else:
            match_result["kill_participation_rate"] = 0
        
        match_result["win"] = bool(participant['win'])
        match_result["total_minions_killed"] = participant['totalMinionsKilled']
        match_result["neutral_minions_killed"] = participant['neutralMinionsKilled']
        match_result["totalDamageDealtToChampions"] = participant['totalDamageDealtToChampions']
        match_result["totalDamageTaken"] = participant['totalDamageTaken']
        match_result["wardsPlaced"] = participant['wardsPlaced']
        match_result["wardsKilled"] = participant['wardsKilled']
        match_result["individualPosition"] = participant.get('individualPosition', 'Unknown')

        return match_result
    except Exception as e:
        return {"error": str(e)}
