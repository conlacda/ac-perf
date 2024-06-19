from constants import (
    ALL_PARTICIPANTS_ROUNDED_PERF_HISTORY,
    AVG_PERF_DUMP,
    COMPETITION_HISTORY_URL,
    CONTEST_TYPE,
    PERF_BY_RANKING,
    RESULT_URL,
)
from typing import List
import json
from os import path
from contest import Contest
from fetch import fetch
from tqdm import tqdm
from logger import logger
import math


def load_saved_rounded_innner_perf(username: str, contest_type: CONTEST_TYPE) -> dict[str, List[int]]:
    """
    Load the perf of user.
    @return dict {
        'InnerPerformance': [],
        'RoundedPerformance': [],
    }
    """
    with open(f"competition-history/{contest_type}/{username}.json", "r") as f:
        return json.load(f)


def dump_avg_innerperformance_all_participants(data: dict[str, (int | float)], contest: Contest) -> None:
    f = open(AVG_PERF_DUMP[contest.type].format(contest.short_name), "w")
    json.dump(data, f, indent=4)
    f.close()


# This function is only for the heuristic contests.
# Because to calculate rating of an user in the heuristic contests we need all competition history
# not last as the algo contests
def dump_participants_competition_history(data: dict[str, List[int]], contest: Contest) -> None:
    f = open(ALL_PARTICIPANTS_ROUNDED_PERF_HISTORY.format(contest.short_name), "w")
    json.dump(data, f)
    f.close()


def avg_inner_performance_of_user(username: str, contest: Contest) -> (int | float):
    perf: dict[str, List[int]] = load_saved_rounded_innner_perf(username, contest.type)
    perf_arr = perf["InnerPerformance"]
    if len(perf_arr) == 0:
        return contest.new_comer_aperf

    perf_arr.reverse()
    numerator: float = 0
    denominator: float = 0
    for i in range(len(perf_arr)):
        numerator += pow(0.9, i + 1) * perf_arr[i]
        denominator += pow(0.9, i + 1)
    return numerator / denominator


def fetch_user_perf(username: str, contest_type: CONTEST_TYPE) -> dict[str, List[int]]:
    """
    Get the RoundedPerformance & InnerPerformance of an user
    @return
    dict {
        'RoundedPerformance': [100, 2400, ...],
        'InnerPerformance': [100, 3000, ...]
    }
    """
    # Fetch from atcoder
    data = fetch(COMPETITION_HISTORY_URL[contest_type].format(username), "json")
    result: dict[str, List[int]] = {"RoundedPerformance": [], "InnerPerformance": []}
    for item in data:
        if item.get("IsRated"):
            result["RoundedPerformance"].append(item.get("Performance"))
            result["InnerPerformance"].append(item.get("InnerPerformance"))
    return result


def dump_perf_history(
    username: str, rounded_and_inner_perf: dict[str, List[int]], contest_type: CONTEST_TYPE
) -> None:
    with open(f"competition-history/{contest_type}/{username}.json", "w") as json_file:
        json.dump(rounded_and_inner_perf, json_file)


# Update aperf after the contest has the fixed result
def update_rated_participants_perf(contest: Contest) -> None:
    res = fetch(RESULT_URL.format(contest.short_name), "json")
    for item in tqdm(res):
        if item.get("IsRated"):
            # results api does not return InnerPerformance
            # if user has Performance is the max performance, then get InnerPerformance from user's competition history
            # otherwise, just update InnerPerformance by Performance
            username: str = item.get("UserScreenName")
            rounded_performance = item.get("Performance")
            inner_performance = item.get("InnerPerformance")
            # If someone joins the contest at the last minute and has no the perf history file.
            # Their perf history should be fetched from Atcoder
            if rounded_performance == contest.max_perf or not path.exists(
                f"competition-history/{contest.type}/{username}.json"
            ):
                perfs = fetch_user_perf(username, contest.type)
                dump_perf_history(username, perfs, contest.type)
            else:
                perfs: dict[str, List[int]] = load_saved_rounded_innner_perf(username, contest.type)
                # perfs.append(rounded_performance)
                perfs['InnerPerformance'].append(inner_performance)
                perfs['RoundedPerformance'].append(rounded_performance)
                dump_perf_history(username, perfs, contest.type)


def get_avg_inner_perf_all_participants(contest: Contest) -> List[float]:
    """
    Get the participants of contest.
    Download all performance history of every participants
    Calculate the average inner performance of them then return
    Because we do not need order, so just return an array [aperf1, aperf2,...]
    """
    participants: List[str] = contest.get_participants(only_rated=True)
    logger.info(f"{len(participants)} rated users joined {contest.short_name}")

    # Download the competition performance of participant if not exists
    print("Download the competition history of all participants")
    for participant in tqdm(participants):
        if not path.exists(f"competition-history/{contest.type}/{participant}.json"):
            perfs: dict[str, List[int]] = fetch_user_perf(participant, contest.type)
            dump_perf_history(participant, perfs, contest.type)

    # Generate avg_perf at data/{contest_name}_avg_perf.json
    data: dict[str, (int | float)] = {}
    print("Calculate average inner performance of every participant")
    for participant in tqdm(participants):
        data[participant] = avg_inner_performance_of_user(participant, contest)

    # Actually, we dont need to dump this file. Just for checking if the result prediction gets wrong.
    dump_avg_innerperformance_all_participants(data, contest)

    # Return the list of aperf (in order to calculate performance during contest)
    return data.values()


# From the avg of all users, calculate the performance X of user with ranking r using binary search
def dump_rank_to_perf(contest: Contest, avg_innerperf: List[float]) -> None:
    """
    Calculate performance of rank r
    based on the average innerperformance of all participants in contest
    """
    # Calculate performance for each ranking
    logger.info(f"Calculating the performance table of contest {contest.short_name}")
    perf_during_contest: List[int] = [] * len(avg_innerperf)
    n = len(avg_innerperf)
    print(f"Calculate performance based on rank in contest {contest.short_name} (binary search) - dump to {PERF_BY_RANKING[contest.type].format(contest.short_name)}")

    def perf2Rank(perf):
        ans = 0
        for aperf in avg_innerperf:
            ans += 1 / (1 + pow(6.0, (perf - aperf) / 400.0))
        ans += 0.5
        return math.ceil(ans)

    prev_left = -5000
    prev_right = 7000
    for i in tqdm(range(n)):
        r = i + 1
        left = prev_left
        right = prev_right
        while left < right:
            mid = (left + right) // 2

            if perf2Rank(mid) <= r:
                right = mid
            else:
                left = mid + 1

        assert left == right
        while perf2Rank(left) < r:
            left -= 1

        perf_during_contest.append(min(left, contest.max_perf))
        # Instead calculate perf(r) with left = -5000 and right = 7000 one more time
        # Notice that perf(r) and perf(r+1) pretty close (perf(r) - perf(r+1) < 50)
        # So we just need to do binary search in (perf(r)-50, perf(r)) to find perf(r+1)
        prev_left = left
        prev_right = left

    # Dump to file
    f = open(PERF_BY_RANKING[contest.type].format(contest.short_name), "w")
    json.dump(perf_during_contest, f)
    f.close()

    return perf_during_contest


def dump_rounded_perf_history_all_participants(contest: Contest) -> None:
    participants: List[str] = contest.get_participants(only_rated=True)

    # Get the list of participants, then fetch the competition history of users if it does not exist.
    data: dict[str, List[int]] = {}
    print(
        f"Generate the competition history of participants in contest {contest.short_name} (rouned perf history)"
    )
    for participant in tqdm(participants):
        if not path.exists(f"competition-history/{contest.type}/{participant}.json"):
            perfs: dict[str, List[int]] = fetch_user_perf(participant, contest.type)
            dump_perf_history(participant, perfs, contest.type)

        perfs = load_saved_rounded_innner_perf(participant, contest.type)
        data[participant] = perfs.get('RoundedPerformance')

    dump_participants_competition_history(data, contest)
