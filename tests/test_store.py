from app.models import (
    AnalysisHistoryEntry,
    DemoProfileSummary,
    OrderHistoryEntry,
    PhotoAnalysisResult,
    RecommendationPlan,
    SessionState,
    SkinProfile,
    SkinType,
    UserContext,
)
from app.store import SessionStore


def test_store_save_and_get_roundtrip(tmp_path) -> None:
    store = SessionStore(str(tmp_path / 'sessions.sqlite3'))
    session = SessionState(
        session_id='session-test',
        photo_analysis=PhotoAnalysisResult(),
        skin_profile=SkinProfile(skin_type=SkinType.normal, primary_concerns=[], confidence_overall=0.8),
        current_plan=RecommendationPlan(required_categories=[]),
        user_preferences=UserContext(),
    )
    store.save(session)
    loaded = store.get('session-test')
    assert loaded is not None
    assert loaded.session_id == 'session-test'


def test_store_persists_profile_analysis_and_order_history(tmp_path) -> None:
    store = SessionStore(str(tmp_path / 'sessions.sqlite3'))
    profile = DemoProfileSummary(
        user_id='demo-user',
        name='Demo user',
        beauty_summary='summary',
        skin_snapshot=[],
        sensitivity_exclusions=[],
        halal_preference='not locked',
        preferred_finish=[],
        preferred_coverage=[],
        budget_direction='same',
        future_features=[],
    )
    store.save_profile(profile)
    assert store.get_profile('demo-user') is not None

    analysis = AnalysisHistoryEntry(
        analysis_id='analysis-1',
        session_id='session-test',
        created_at='2026-04-10T10:00:00+00:00',
        headline='Beauty ID scan',
        metrics={'oiliness': 0.5},
    )
    store.add_analysis_history('demo-user', analysis)
    assert store.list_analysis_history('demo-user')[0].analysis_id == 'analysis-1'

    order = OrderHistoryEntry(
        order_id='order-1',
        session_id='session-test',
        created_at='2026-04-10T10:01:00+00:00',
        total_items=1,
        total_price=1000,
    )
    store.add_order_history('demo-user', order)
    assert store.list_order_history('demo-user')[0].order_id == 'order-1'
