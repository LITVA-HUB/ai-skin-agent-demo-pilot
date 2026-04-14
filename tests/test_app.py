from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health() -> None:
    response = client.get('/health')
    assert response.status_code == 200
    assert response.json()['status'] == 'ok'


def test_analyze_makeup_and_followup() -> None:
    analyze = client.post('/v1/photo/analyze', json={
        'image_url': 'https://example.com/photo.jpg',
        'user_context': {
            'budget_segment': 'mid',
            'preferred_brands': [],
            'excluded_ingredients': [],
            'routine_size': 'standard',
            'goal': 'pick foundation for my skin tone, want light coverage and radiant finish'
        }
    })
    assert analyze.status_code == 200
    body = analyze.json()
    assert body['session_id']
    assert body['recommendations']
    assert any(item['category'] in {'foundation', 'skin_tint'} for item in body['recommendations'])

    session_id = body['session_id']
    followup = client.post(f'/v1/session/{session_id}/message', json={'message': 'need concealer under eye'})
    assert followup.status_code == 200
    follow = followup.json()
    assert follow['intent']['action'] == 'recommend'
    assert follow['intent']['target_category'] == 'concealer'
    assert any(x['category'] == 'concealer' for x in follow['recommendations'])


def test_compare_and_explain_modes() -> None:
    analyze = client.post('/v1/photo/analyze', json={
        'image_url': 'https://example.com/compare.jpg',
        'user_context': {
            'budget_segment': 'mid',
            'preferred_brands': [],
            'excluded_ingredients': [],
            'routine_size': 'standard',
            'goal': 'want foundation and concealer with a natural finish'
        }
    })
    session_id = analyze.json()['session_id']

    compare_resp = client.post(f'/v1/session/{session_id}/message', json={'message': 'compare foundation and concealer'})
    assert compare_resp.status_code == 200
    compare_data = compare_resp.json()
    assert compare_data['intent']['action'] == 'compare'
    assert compare_data['intent']['domain'] == 'makeup'
    assert compare_data['answer_text']
    assert len(compare_data['answer_text']) > 20

    explain_resp = client.post(f'/v1/session/{session_id}/message', json={'message': 'explain why this concealer works'})
    assert explain_resp.status_code == 200
    explain_data = explain_resp.json()
    assert explain_data['intent']['action'] == 'explain'
    assert explain_data['answer_text']
    assert len(explain_data['answer_text']) > 20


def test_cart_flow_add_update_remove() -> None:
    analyze = client.post('/v1/photo/analyze', json={
        'image_url': 'https://example.com/cart.jpg',
        'user_context': {
            'budget_segment': 'mid',
            'preferred_brands': [],
            'excluded_ingredients': [],
            'routine_size': 'standard',
            'goal': 'pick foundation for my skin tone'
        }
    })
    assert analyze.status_code == 200
    body = analyze.json()
    session_id = body['session_id']
    product = body['recommendations'][0]

    add_resp = client.post(f'/v1/session/{session_id}/cart/items', json={'sku': product['sku']})
    assert add_resp.status_code == 200
    add_data = add_resp.json()
    assert add_data['total_items'] == 1
    assert add_data['total_price'] == product['price_value']

    patch_resp = client.patch(f"/v1/session/{session_id}/cart/items/{product['sku']}", json={'quantity': 3})
    assert patch_resp.status_code == 200
    patch_data = patch_resp.json()
    assert patch_data['total_items'] == 3
    assert patch_data['total_price'] == product['price_value'] * 3

    delete_resp = client.delete(f"/v1/session/{session_id}/cart/items/{product['sku']}")
    assert delete_resp.status_code == 200
    delete_data = delete_resp.json()
    assert delete_data['total_items'] == 0
    assert delete_data['total_price'] == 0


def test_cart_ignores_client_product_fields() -> None:
    analyze = client.post('/v1/photo/analyze', json={
        'image_url': 'https://example.com/cart-authoritative.jpg',
        'user_context': {
            'budget_segment': 'mid',
            'preferred_brands': [],
            'excluded_ingredients': [],
            'routine_size': 'standard',
            'goal': 'pick foundation'
        }
    })
    body = analyze.json()
    session_id = body['session_id']
    product = body['recommendations'][0]

    add_resp = client.post(f'/v1/session/{session_id}/cart/items', json={
        'sku': product['sku'],
        'title': 'Tampered Title',
        'brand': 'Tampered Brand',
        'price_value': 1,
    })
    assert add_resp.status_code == 200
    item = add_resp.json()['cart']['items'][0]
    assert item['title'] == product['title']
    assert item['brand'] == product['brand']
    assert item['price_value'] == product['price_value']



def test_mixed_domain_memory_and_preference_updates() -> None:
    analyze = client.post('/v1/photo/analyze', json={
        'image_url': 'https://example.com/hybrid.jpg',
        'user_context': {
            'budget_segment': 'mid',
            'preferred_brands': [],
            'excluded_ingredients': [],
            'routine_size': 'standard',
            'goal': 'build a skincare routine and pick a skin tint'
        }
    })
    session_id = analyze.json()['session_id']
    response = client.post(
        f'/v1/session/{session_id}/message',
        json={'message': 'make the routine minimal but keep skin tint, I want matte finish and no niacinamide'}
    )
    assert response.status_code == 200
    data = response.json()
    assert data['intent']['domain'] == 'hybrid'
    assert data['updated_session_state']['user_preferences']['routine_size'] == 'minimal'
    assert data['updated_session_state']['user_preferences']['excluded_ingredients'] == ['niacinamide']
    assert data['updated_session_state']['user_preferences']['preferred_finish'] == ['matte']


def test_hybrid_domain_from_goal() -> None:
    analyze = client.post('/v1/photo/analyze', json={
        'image_url': 'https://example.com/3.jpg',
        'user_context': {
            'budget_segment': 'mid',
            'preferred_brands': [],
            'excluded_ingredients': [],
            'routine_size': 'standard',
            'goal': 'want skincare routine and foundation with light coverage'
        }
    })
    assert analyze.status_code == 200
    data = analyze.json()
    assert set(data['recommendation_plan']['product_domains']) == {'skincare', 'makeup'}
    categories = {item['category'] for item in data['recommendations']}
    assert {'cleanser', 'moisturizer', 'spf', 'foundation'}.issubset(categories)


def test_analyze_photo_does_not_auto_accept_unshown_products() -> None:
    analyze = client.post('/v1/photo/analyze', json={
        'image_url': 'https://example.com/shown-vs-accepted.jpg',
        'user_context': {
            'budget_segment': 'mid',
            'preferred_brands': [],
            'excluded_ingredients': [],
            'routine_size': 'standard',
            'accepted_products': ['NON_EXISTING_SKU'],
            'goal': 'pick foundation and concealer'
        }
    })
    assert analyze.status_code == 200
    session_id = analyze.json()['session_id']
    session = client.get(f'/v1/session/{session_id}').json()
    assert session['accepted_products'] == []


def test_followup_rejected_products_stay_within_shown_products() -> None:
    analyze = client.post('/v1/photo/analyze', json={
        'image_url': 'https://example.com/rejected-scope.jpg',
        'user_context': {
            'budget_segment': 'mid',
            'preferred_brands': [],
            'excluded_ingredients': [],
            'routine_size': 'standard',
            'goal': 'pick foundation and concealer'
        }
    })
    session_id = analyze.json()['session_id']
    followup = client.post(f'/v1/session/{session_id}/message', json={'message': 'сделай дешевле'})
    assert followup.status_code == 200
    state = followup.json()['updated_session_state']
    shown = set(state['shown_products'])
    rejected = set(state['rejected_products'])
    assert rejected.issubset(shown)



def test_session_stores_raw_conversation_turns() -> None:
    analyze = client.post('/v1/photo/analyze', json={
        'image_url': 'https://example.com/memory-store.jpg',
        'user_context': {
            'budget_segment': 'mid',
            'preferred_brands': [],
            'excluded_ingredients': [],
            'routine_size': 'standard',
            'goal': 'pick skincare routine and skin tint'
        }
    })
    session_id = analyze.json()['session_id']

    followup = client.post(f'/v1/session/{session_id}/message', json={'message': 'сделай подборку дешевле'})
    assert followup.status_code == 200
    history = followup.json()['updated_session_state']['conversation_history']

    assert len(history) >= 3
    assert history[0]['role'] == 'assistant'
    assert history[1]['role'] == 'user'
    assert history[1]['message'] == 'сделай подборку дешевле'
    assert history[2]['role'] == 'assistant'
    assert history[2]['message']



def test_conversation_memory_recall_uses_session_history() -> None:
    analyze = client.post('/v1/photo/analyze', json={
        'image_url': 'https://example.com/memory-recall.jpg',
        'user_context': {
            'budget_segment': 'mid',
            'preferred_brands': [],
            'excluded_ingredients': [],
            'routine_size': 'standard',
            'goal': 'pick foundation for my skin tone'
        }
    })
    session_id = analyze.json()['session_id']

    client.post(f'/v1/session/{session_id}/message', json={'message': 'подбери консилер под глаза'})
    client.post(f'/v1/session/{session_id}/message', json={'message': 'сделай вариант подешевле'})
    recall = client.post(f'/v1/session/{session_id}/message', json={'message': 'что я у тебя спрашивал?'})

    assert recall.status_code == 200
    data = recall.json()
    assert data['intent']['intent'] == 'conversation_memory'
    assert 'подбери консилер под глаза' in data['answer_text']
    assert 'сделай вариант подешевле' in data['answer_text']
    assert 'что я у тебя спрашивал?' not in data['answer_text']



def test_conversation_memory_recall_previous_selection() -> None:
    analyze = client.post('/v1/photo/analyze', json={
        'image_url': 'https://example.com/memory-selection.jpg',
        'user_context': {
            'budget_segment': 'mid',
            'preferred_brands': [],
            'excluded_ingredients': [],
            'routine_size': 'standard',
            'goal': 'pick foundation and concealer'
        }
    })
    session_id = analyze.json()['session_id']

    client.post(f'/v1/session/{session_id}/message', json={'message': 'подбери консилер под глаза'})
    recall = client.post(f'/v1/session/{session_id}/message', json={'message': 'напомни прошлую подборку'})

    assert recall.status_code == 200
    data = recall.json()
    assert data['intent']['intent'] == 'conversation_memory'
    assert 'Напоминаю прошлую подборку' in data['answer_text']
    assert len(data['updated_session_state']['conversation_history']) >= 5


def test_allergen_and_halal_filters_affect_recommendations() -> None:
    analyze = client.post('/v1/photo/analyze', json={
        'image_url': 'https://example.com/filter.jpg',
        'user_context': {
            'goal': 'need skincare and complexion set',
        }
    })
    assert analyze.status_code == 200
    session_id = analyze.json()['session_id']

    filtered = client.post(f'/v1/session/{session_id}/message', json={'message': 'без niacinamide и халяль'})
    assert filtered.status_code == 200
    data = filtered.json()
    prefs = data['updated_session_state']['user_preferences']
    assert prefs['halal_only'] is True
    assert 'niacinamide' in prefs['excluded_ingredients'] or 'niacinamide' in prefs['excluded_sensitivity_triggers']
    assert all(item['halal_status'] in {'friendly', 'certified'} for item in data['recommendations'])
    assert all('niacinamide' not in (item.get('why','').lower()) for item in data['recommendations'])



def test_analysis_history_and_beauty_scan_are_returned() -> None:
    analyze = client.post('/v1/photo/analyze', json={
        'image_url': 'https://example.com/history.jpg',
        'user_context': {'goal': 'pick skin tint and serum'}
    })
    assert analyze.status_code == 200
    body = analyze.json()
    assert body['beauty_scan']['metrics']
    assert body['beauty_scan']['zones']
    cabinet = client.get('/v1/profile/demo')
    assert cabinet.status_code == 200
    cabinet_data = cabinet.json()
    assert cabinet_data['analysis_history']
    assert cabinet_data['profile']['beauty_summary']



def test_checkout_saves_order_history_and_clears_cart() -> None:
    analyze = client.post('/v1/photo/analyze', json={
        'image_url': 'https://example.com/checkout.jpg',
        'user_context': {'goal': 'pick foundation'}
    })
    session_id = analyze.json()['session_id']
    sku = analyze.json()['recommendations'][0]['sku']
    add = client.post(f'/v1/session/{session_id}/cart/items', json={'sku': sku})
    assert add.status_code == 200

    checkout = client.post(f'/v1/session/{session_id}/checkout', json={})
    assert checkout.status_code == 200
    checkout_data = checkout.json()
    assert checkout_data['cart_cleared'] is True
    assert checkout_data['order']['total_items'] == 1

    cart = client.get(f'/v1/session/{session_id}/cart')
    assert cart.status_code == 200
    assert cart.json()['total_items'] == 0

    cabinet = client.get('/v1/profile/demo').json()
    assert cabinet['order_history']
