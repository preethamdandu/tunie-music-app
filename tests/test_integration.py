import os
import unittest
from unittest.mock import patch, MagicMock


class _Ctx:
    def __enter__(self):
        return self
    def __exit__(self, exc_type, exc, tb):
        return False


def _stub_streamlit_for_show_playlist(keywords: str):
    """Build a dict of streamlit st.* stubs sufficient to run show_playlist_generation."""
    stubs = {
        'markdown': MagicMock(),
        'info': MagicMock(),
        'warning': MagicMock(),
        'success': MagicMock(),
        'caption': MagicMock(),
        'button': MagicMock(return_value=False),
        'columns': MagicMock(return_value=(_Ctx(), _Ctx(), _Ctx(), _Ctx())),
        'form': MagicMock(return_value=_Ctx()),
        'form_submit_button': MagicMock(return_value=True),
        'selectbox': MagicMock(side_effect=[
            'Happy',      # mood
            'Working',    # activity
            'Any Language'  # language
        ]),
        'text_area': MagicMock(return_value=''),
        'text_input': MagicMock(return_value=keywords),
        'radio': MagicMock(return_value='Quick Select'),
        'slider': MagicMock(return_value=10),
        'number_input': MagicMock(return_value=20),
        'spinner': MagicMock(return_value=_Ctx()),
        'plotly_chart': MagicMock(),
        'dataframe': MagicMock(),
        'expander': MagicMock(return_value=_Ctx()),
        'checkbox': MagicMock(return_value=False),
    }
    return stubs


class TestIntegrationIntentClassifier(unittest.TestCase):
    @patch.dict(os.environ, {'FEATURE_FLAG_LLM_DRIVEN': 'False'}, clear=False)
    def test_niche_intent_bad_bunny_routes_to_niche_query(self):
        import app  # import here to patch attributes on the loaded module

        # Mock streamlit api used in show_playlist_generation
        stubs = _stub_streamlit_for_show_playlist('bad bunny')
        with patch.object(app, 'st') as st, \
             patch.object(app.IntentClassifier, 'classify', return_value='niche_query'):
            for k, v in stubs.items():
                setattr(st, k, v)

            # Mock workflow readiness and capture workflow calls
            mock_workflow = MagicMock()
            with patch.object(app, 'check_workflow_ready', return_value=(True, mock_workflow)):
                # Execute
                app.show_playlist_generation()

        # Assert called with niche_query strategy
        called = False
        for _, kwargs in mock_workflow.execute_workflow.call_args_list:
            if kwargs.get('strategy') == 'niche_query':
                called = True
                break
        self.assertTrue(called, 'execute_workflow was not called with strategy="niche_query" for "bad bunny"')

    @patch.dict(os.environ, {'FEATURE_FLAG_LLM_DRIVEN': 'False'}, clear=False)
    def test_general_intent_upbeat_workout_routes_to_default_cf_first(self):
        import app

        stubs = _stub_streamlit_for_show_playlist('upbeat workout')
        with patch.object(app, 'st') as st, \
             patch.object(app.IntentClassifier, 'classify', return_value='cf_first'):
            for k, v in stubs.items():
                setattr(st, k, v)

            mock_workflow = MagicMock()
            with patch.object(app, 'check_workflow_ready', return_value=(True, mock_workflow)):
                app.show_playlist_generation()

        # Assert called with default strategy 'cf_first' (feature flag is False)
        called = False
        for _, kwargs in mock_workflow.execute_workflow.call_args_list:
            if kwargs.get('strategy') == 'cf_first':
                called = True
                break
        self.assertTrue(called, 'execute_workflow was not called with strategy="cf_first" for general keywords')


if __name__ == '__main__':
    unittest.main()


