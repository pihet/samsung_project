"""
BuyOrWait Daily Batch Collector Module
- 매일 1회(새벽 6시) 다나와 인기 급상승 상품 및 카테고리 대표 상품 최저가를 PostgreSQL에 사전 수집(Pre-fetching)합니다.
- APScheduler 백그라운드 스케줄러 내장
- PostgreSQL 덮어쓰기(UPSERT) 및 3년 이상 오래된 이력 자동 삭제(Cleanup)로 DB 용량 완벽 통제
"""

import sys
import os
import time
from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler

import collector
import analyzer
import database
import db_manager

# 글로벌 스케줄러 인스턴스 싱글톤
_scheduler = None

def cleanup_old_price_history(days=1095, db_pass=None):
    """3년(1095일) 이상 된 오래된 가격 이력 레코드 자동 삭제하여 DB 용량 유지"""
    try:
        conn = database.get_connection(db_pass=db_pass)
        cursor = conn.cursor()
        cutoff_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("DELETE FROM raw_price_logs WHERE crawled_at < %s", (cutoff_date,))
        deleted_count = cursor.rowcount
        conn.commit()
        conn.close()
        print(f"[daily_collector.py] 오래된 raw_price_logs 정리 완료: {deleted_count}건 삭제 (기준: {cutoff_date} 이전)")
    except Exception as e:
        print(f"[daily_collector.py] 오래된 이력 삭제 중 오류: {e}")

def run_daily_batch(db_pass=None):
    """
    하루 1회 일괄 수집 핵심 배치 함수:
    1. 실시간 급상승 대표 키워드 4종 수집 & raw_price_logs DB 저장
    2. 오래된 가격 이력 정리 (DB 용량 통제)
    3. 데이터 마트(dm_daily_price_clean) 동기화 배치 실행
    """
    print(f"\n==================================================")
    print(f"[daily_collector.py] 하루 1회 배치 수집 시작: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"==================================================")

    db_p = db_pass if db_pass else "1111"

    # 1. 실시간 급상승 키워드 대표 4종 수집
    popular_keywords = ["ddr5 16gb", "9800x3d", "제습기", "닌텐도 스위치 2"]
    collected_cnt = 0

    for kw in popular_keywords:
        try:
            items, _ = collector.search_shopping_products_realtime(kw, display=1)
            if items and len(items) > 0:
                item = items[0]
                p_id = str(item['product_id'])
                lprice = item['lprice']
                clean_title = analyzer.clean_product_name(item['title'])
                
                database.save_product_and_price(
                    product_id=p_id,
                    title=clean_title,
                    category=item.get('category', '디지털/가전'),
                    image_url=item.get('image_url', ''),
                    mall_name=item.get('mall_name', '다나와 최저가몰'),
                    link=item.get('link', 'https://prod.danawa.com'),
                    price=lprice,
                    db_pass=db_p
                )
                collected_cnt += 1
                print(f"  [수집 완료] {kw} -> {clean_title} ({lprice:,}원)")
        except Exception as e:
            print(f"  [수집 실패] {kw}: {e}")

    # 2. 3년 초과 오래된 데이터 정리
    cleanup_old_price_history(days=1095, db_pass=db_p)

    # 3. 데이터 마트(dm_daily_price_clean) 동기화 가공 배치 실행
    try:
        database.update_data_mart(db_pass=db_p)
    except Exception as e:
        print(f"  [데이터 마트 동기화 오류]: {e}")


    # 4. 전체 회원의 찜한 상품 목표가 달성 여부 일괄 탐지 및 알림 메일 자동 발송
    sent_cnt, alert_msg = db_manager.check_all_users_target_price_alerts(db_pass=db_p)
    print(f"  [배치 알림] {alert_msg}")

    print(f"==================================================")
    print(f"[daily_collector.py] 배치 완료: 총 {collected_cnt}개 키워드 DB & 데이터 마트 갱신 완료")
    print(f"==================================================\n")


def start_scheduler(db_pass=None):
    """APScheduler 백그라운드 스케줄러 시작 (매일 새벽 06:00 AM 실행)"""
    global _scheduler
    if _scheduler is not None and _scheduler.running:
        return _scheduler

    _scheduler = BackgroundScheduler(timezone="Asia/Seoul")
    # 매일 새벽 06:00 실행 등록
    _scheduler.add_job(
        func=run_daily_batch,
        trigger="cron",
        hour=6,
        minute=0,
        id="daily_danawa_batch_job",
        replace_existing=True,
        args=[db_pass]
    )
    _scheduler.start()
    print(f"[daily_collector.py] APScheduler 백그라운드 스케줄러 구동 완료 (매일 06:00 AM 배치 실행 설정)")
    return _scheduler

if __name__ == "__main__":
    # 터미널에서 direct 실행 시 수동 1회 수집 구동
    print("[daily_collector.py] 수동 1회 일괄 수집 모드 실행...")
    database.init_db()
    run_daily_batch()
