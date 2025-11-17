"""
Ticker - A scheduled object that ticks every N seconds

This demonstrates scheduled execution. The ticker:
- Starts ticking when start() is called
- Increments a counter every N seconds
- Logs each tick
- Can be stopped with stop()
- Tests scheduled execution (dogfooding!)
"""

# Runtime injection (will be provided by ObjectRuntime)
_logger = None
_state_manager = None
_schedule = None
_unschedule = None


def start(request=None):
    """
    Start ticking every 2 seconds

    This is called via POST /objects/basics_ticker?action=start
    """
    interval = 2  # Tick every 2 seconds

    # Initialize counter
    if _state_manager:
        _state_manager.set('ticks', 0)
        _state_manager.set('running', True)

    # Schedule tick() to run every 2 seconds
    if _schedule:
        _schedule(interval, 'tick')

    if _logger:
        _logger.info(f'Ticker started - will tick every {interval}s', interval=interval)

    return {
        'status': 'ok',
        'message': f'Ticker started (interval={interval}s)',
        'interval': interval
    }


def tick():
    """
    This gets called every N seconds by the scheduler

    Not called via HTTP - scheduler calls it automatically
    """
    if not _state_manager:
        return

    # Increment counter
    ticks = _state_manager.get('ticks', 0)
    ticks += 1
    _state_manager.set('ticks', ticks)
    _state_manager.set('last_tick', __import__('time').time())

    if _logger:
        _logger.info(f'Tick #{ticks}', ticks=ticks)

    return {'ticks': ticks}


def stop(request=None):
    """
    Stop ticking

    This is called via POST /objects/basics_ticker?action=stop
    """
    # Unschedule tick()
    if _unschedule:
        _unschedule('tick')

    if _state_manager:
        _state_manager.set('running', False)

    if _logger:
        _logger.warning('Ticker stopped')

    return {
        'status': 'ok',
        'message': 'Ticker stopped'
    }


def GET(request):
    """Get current ticker status"""
    if not _state_manager:
        return {'status': 'error', 'message': 'No state manager'}

    ticks = _state_manager.get('ticks', 0)
    running = _state_manager.get('running', False)
    last_tick = _state_manager.get('last_tick', None)

    return {
        'status': 'ok',
        'ticks': ticks,
        'running': running,
        'last_tick': last_tick,
        'message': f'Ticker has ticked {ticks} times'
    }


def test_ticker_starts():
    """Test that ticker can be started"""
    if not _schedule:
        return {'status': 'skip', 'reason': 'No scheduler available'}

    # Start ticker
    result = start()

    # Verify
    assert result['status'] == 'ok', f"Expected status=ok, got {result['status']}"
    assert _state_manager.get('running') == True, "Ticker should be running"
    assert _state_manager.get('ticks') == 0, "Should start at 0 ticks"

    if _logger:
        _logger.info('test_ticker_starts passed')

    return {'status': 'pass', 'test': 'test_ticker_starts'}


def test_ticker_stops():
    """Test that ticker can be stopped"""
    if not _unschedule:
        return {'status': 'skip', 'reason': 'No scheduler available'}

    # Start then stop
    start()
    result = stop()

    # Verify
    assert result['status'] == 'ok', f"Expected status=ok, got {result['status']}"
    assert _state_manager.get('running') == False, "Ticker should be stopped"

    if _logger:
        _logger.info('test_ticker_stops passed')

    return {'status': 'pass', 'test': 'test_ticker_stops'}


__endpoint__ = {
    'name': 'ticker',
    'description': 'A scheduled object that ticks every N seconds',
    'version': '1.0.0',
    'methods': ['GET'],
    'self_logging': True,
    'self_testing': True,
    'scheduled': True,  # This object uses scheduled execution
}
