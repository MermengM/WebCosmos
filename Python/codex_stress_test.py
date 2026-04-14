import random
import string
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime
from statistics import mean
from typing import Dict, List, Optional, Tuple

import requests
from openai import OpenAI


QUESTION_TEMPLATES = [
	"Hi",
]


@dataclass
class RequestResult:
	task_id: int
	run_id: str
	nonce: str
	ok: bool
	latency_ms: float
	status_code: Optional[int]
	error: Optional[str]
	error_type: Optional[str]
	request_id: Optional[str]
	start_at: float
	end_at: float
	client_type: str


def random_noise(length: int = 16) -> str:
	chars = string.ascii_letters + string.digits
	return "".join(random.choice(chars) for _ in range(length))


def build_random_question() -> Tuple[str, str]:
	base = random.choice(QUESTION_TEMPLATES)
	nonce = uuid.uuid4().hex
	ts = int(time.time() * 1000)
	extra = random_noise(24)
	question = (
		f"{base}\n"
		f"请务必在回答末尾原样返回以下校验串，不要解释：{nonce}\n"
		f"随机戳: {ts}-{extra}"
	)
	return question, nonce


def fmt_ts(ts: float) -> str:
	return datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]


def percentile(sorted_values: List[float], p: float) -> float:
	if not sorted_values:
		return 0.0
	k = (len(sorted_values) - 1) * (p / 100.0)
	f = int(k)
	c = min(f + 1, len(sorted_values) - 1)
	if f == c:
		return sorted_values[f]
	return sorted_values[f] + (sorted_values[c] - sorted_values[f]) * (k - f)


def send_by_requests(
	task_id: int,
	run_id: str,
	base_url: str,
	api_key: str,
	model: str,
	timeout: int,
	max_tokens: int,
	temperature: float,
) -> RequestResult:
	question, nonce = build_random_question()
	endpoint = base_url.rstrip("/") + "/chat/completions"
	payload = {
		"model": model,
		"messages": [{"role": "user", "content": question}],
		"temperature": temperature,
		"max_tokens": max_tokens,
	}
	headers = {
		"Authorization": f"Bearer {api_key}",
		"Content-Type": "application/json",
		"Cache-Control": "no-cache",
		"Pragma": "no-cache",
		"X-Stress-Nonce": uuid.uuid4().hex,
	}

	start_at = time.time()
	start = time.perf_counter()
	try:
		response = requests.post(
			endpoint,
			json=payload,
			headers=headers,
			timeout=timeout,
		)
		end_at = time.time()
		latency_ms = (time.perf_counter() - start) * 1000
		request_id = response.headers.get("x-request-id")

		if 200 <= response.status_code < 300:
			return RequestResult(
				task_id,
				run_id,
				nonce,
				True,
				latency_ms,
				response.status_code,
				None,
				None,
				request_id,
				start_at,
				end_at,
				"requests",
			)

		err_text = response.text[:300].replace("\n", " ")
		return RequestResult(
			task_id,
			run_id,
			nonce,
			False,
			latency_ms,
			response.status_code,
			err_text,
			"http_error",
			request_id,
			start_at,
			end_at,
			"requests",
		)
	except requests.exceptions.Timeout as exc:
		end_at = time.time()
		latency_ms = (time.perf_counter() - start) * 1000
		return RequestResult(
			task_id,
			run_id,
			nonce,
			False,
			latency_ms,
			None,
			str(exc),
			"timeout",
			None,
			start_at,
			end_at,
			"requests",
		)
	except requests.exceptions.RequestException as exc:
		end_at = time.time()
		latency_ms = (time.perf_counter() - start) * 1000
		return RequestResult(
			task_id,
			run_id,
			nonce,
			False,
			latency_ms,
			None,
			str(exc),
			"request_exception",
			None,
			start_at,
			end_at,
			"requests",
		)
	except Exception as exc:
		end_at = time.time()
		latency_ms = (time.perf_counter() - start) * 1000
		return RequestResult(
			task_id,
			run_id,
			nonce,
			False,
			latency_ms,
			None,
			str(exc),
			"unknown_exception",
			None,
			start_at,
			end_at,
			"requests",
		)


def send_by_openai(
	task_id: int,
	run_id: str,
	base_url: str,
	api_key: str,
	model: str,
	timeout: int,
	max_tokens: int,
	temperature: float,
) -> RequestResult:
	question, nonce = build_random_question()
	client = OpenAI(base_url=base_url, api_key=api_key, timeout=timeout)

	start_at = time.time()
	start = time.perf_counter()
	try:
		_ = client.chat.completions.create(
			model=model,
			messages=[{"role": "user", "content": question}],
			temperature=temperature,
			max_tokens=max_tokens,
			extra_headers={
				"Cache-Control": "no-cache",
				"Pragma": "no-cache",
				"X-Stress-Nonce": uuid.uuid4().hex,
			},
		)
		end_at = time.time()
		latency_ms = (time.perf_counter() - start) * 1000
		return RequestResult(
			task_id,
			run_id,
			nonce,
			True,
			latency_ms,
			200,
			None,
			None,
			None,
			start_at,
			end_at,
			"openai",
		)
	except Exception as exc:
		end_at = time.time()
		latency_ms = (time.perf_counter() - start) * 1000
		err_str = str(exc)
		err_type = "timeout" if "timed out" in err_str.lower() else "unknown_exception"
		return RequestResult(
			task_id,
			run_id,
			nonce,
			False,
			latency_ms,
			None,
			err_str,
			err_type,
			None,
			start_at,
			end_at,
			"openai",
		)


def print_detail_log(result: RequestResult) -> None:
	status_txt = "OK" if result.ok else "FAIL"
	status_code = result.status_code if result.status_code is not None else "-"
	err_type = result.error_type if result.error_type else "-"
	request_id = result.request_id if result.request_id else "-"
	err_msg = ""
	if result.error:
		err_msg = result.error.replace("\n", " ")[:160]

	print(
		f"[TASK {result.task_id:04d}] [{status_txt}] "
		f"client={result.client_type} status={status_code} "
		f"latency={result.latency_ms:.2f}ms err_type={err_type} "
		f"run_id={result.run_id} nonce={result.nonce[:8]} "
		f"request_id={request_id} "
		f"start={fmt_ts(result.start_at)} end={fmt_ts(result.end_at)}"
	)
	if err_msg:
		print(f"[TASK {result.task_id:04d}] error={err_msg}")


def run_load_test(
	client_type: str,
	base_url: str,
	api_key: str,
	model: str,
	concurrency: int,
	total_requests: int,
	timeout: int,
	max_tokens: int,
	temperature: float,
) -> List[RequestResult]:
	results: List[RequestResult] = []
	lock = threading.Lock()
	run_id = uuid.uuid4().hex[:10]

	def task(task_id: int) -> RequestResult:
		if client_type == "requests":
			return send_by_requests(
				task_id,
				run_id,
				base_url,
				api_key,
				model,
				timeout,
				max_tokens,
				temperature,
			)
		return send_by_openai(
			task_id,
			run_id,
			base_url,
			api_key,
			model,
			timeout,
			max_tokens,
			temperature,
		)

	with ThreadPoolExecutor(max_workers=concurrency) as executor:
		futures = [executor.submit(task, i + 1) for i in range(total_requests)]
		for future in as_completed(futures):
			result = future.result()
			with lock:
				results.append(result)
			print_detail_log(result)

	return results


def summarize(results: List[RequestResult], title: str) -> Dict[str, float]:
	total = len(results)
	success = sum(1 for r in results if r.ok)
	failed = total - success
	latencies = sorted(r.latency_ms for r in results)
	elapsed_sec = sum(r.latency_ms for r in results) / 1000.0

	stats = {
		"total": float(total),
		"success": float(success),
		"failed": float(failed),
		"success_rate": (success / total * 100.0) if total else 0.0,
		"latency_avg_ms": mean(latencies) if latencies else 0.0,
		"latency_p50_ms": percentile(latencies, 50),
		"latency_p95_ms": percentile(latencies, 95),
		"latency_p99_ms": percentile(latencies, 99),
		"latency_max_ms": max(latencies) if latencies else 0.0,
		"rps_rough": (total / elapsed_sec) if elapsed_sec > 0 else 0.0,
	}

	print("\n" + "=" * 72)
	print(f"[{title}]")
	print("=" * 72)
	print(f"Total Requests : {int(stats['total'])}")
	print(f"Success        : {int(stats['success'])}")
	print(f"Failed         : {int(stats['failed'])}")
	print(f"Success Rate   : {stats['success_rate']:.2f}%")
	print(f"Latency Avg    : {stats['latency_avg_ms']:.2f} ms")
	print(f"Latency P50    : {stats['latency_p50_ms']:.2f} ms")
	print(f"Latency P95    : {stats['latency_p95_ms']:.2f} ms")
	print(f"Latency P99    : {stats['latency_p99_ms']:.2f} ms")
	print(f"Latency Max    : {stats['latency_max_ms']:.2f} ms")
	print(f"RPS (rough)    : {stats['rps_rough']:.2f}")

	timeout_failed = sum(1 for r in results if not r.ok and r.error_type == "timeout")
	http_failed = sum(1 for r in results if not r.ok and r.error_type == "http_error")
	other_failed = failed - timeout_failed - http_failed
	print(f"Fail Timeout   : {timeout_failed}")
	print(f"Fail HTTP      : {http_failed}")
	print(f"Fail Other     : {other_failed}")

	sample_errors = [r for r in results if not r.ok][:5]
	if sample_errors:
		print("\nSample Errors (up to 5):")
		for idx, item in enumerate(sample_errors, start=1):
			print(
				f"{idx}. status={item.status_code}, latency={item.latency_ms:.2f} ms, error={item.error}"
			)

	return stats




if __name__ == "__main__":
	# 在这里硬编码配置，直接修改这些变量即可压测
	base_url = "http://192.168.1.100:34567/v1"
	## A
	# api_key = "sk-965ed9b914dc538484504004b5c8c229392a58ccbcb3a26f389c4360f6640847"
	## B
	api_key = "sk-1b014d1dae4c741377ad257cc7f8513f212c687633c06035accdd84c553d81d1"

	
	model = "GP5-5.4 Mini"
	total = 60  # 请求总次数
	# 单次并发压测: 并发数直接等于总请求数
	concurrency = total
	timeout = 60
	max_tokens = 128
	temperature = 0.7

	if concurrency <= 0 or total <= 0 or timeout <= 0 or max_tokens <= 0:
		raise ValueError("concurrency/total/timeout/max_tokens must be > 0")

	print("Load test started with params:")
	print(f"base_url    : {base_url}")
	print(f"model       : {model}")
	print("client      : requests")
	print(f"concurrency : {concurrency}")
	print(f"total       : {total}")
	print(f"timeout     : {timeout}s")

	results_req = run_load_test(
		client_type="requests",
		base_url=base_url,
		api_key=api_key,
		model=model,
		concurrency=concurrency,
		total_requests=total,
		timeout=timeout,
		max_tokens=max_tokens,
		temperature=temperature,
	)
	summarize(results_req, "requests client")

