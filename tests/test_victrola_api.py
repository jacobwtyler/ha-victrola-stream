"""Tests for VictrolaAPI - tests the API layer with mocked HTTP."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from aiohttp import ClientSession
from custom_components.victrola_stream.victrola_api import VictrolaAPI


@pytest.fixture
def api():
    return VictrolaAPI("192.168.1.100", 80)


class TestVictrolaAPIInit:
    def test_default_port(self):
        api = VictrolaAPI("10.0.0.1")
        assert api.host == "10.0.0.1"
        assert api.port == 80
        assert api.base_url == "http://10.0.0.1:80"

    def test_custom_port(self):
        api = VictrolaAPI("10.0.0.1", 8080)
        assert api.port == 8080
        assert api.base_url == "http://10.0.0.1:8080"


class TestSetDataPayloads:
    """Test that API methods build correct payloads."""

    @pytest.mark.asyncio
    async def test_set_audio_quality_calls_set_data(self, api):
        api.async_set_data = AsyncMock(return_value=True)
        result = await api.async_set_audio_quality("losslessQuality")
        assert result is True
        api.async_set_data.assert_called_once_with(
            "settings:/victrola/forceLowBitrate",
            "value",
            {"forceLowBitrate": "losslessQuality", "type": "forceLowBitrate"},
        )

    @pytest.mark.asyncio
    async def test_set_audio_latency_calls_set_data(self, api):
        api.async_set_data = AsyncMock(return_value=True)
        result = await api.async_set_audio_latency("med")
        assert result is True
        api.async_set_data.assert_called_once_with(
            "settings:/victrola/wirelessAudioDelay",
            "value",
            {"adchlsLatency": "med", "type": "adchlsLatency"},
        )

    @pytest.mark.asyncio
    async def test_set_rca_mode_calls_set_data(self, api):
        api.async_set_data = AsyncMock(return_value=True)
        await api.async_set_rca_mode("simultaneous")
        api.async_set_data.assert_called_once_with(
            "settings:/adchls/dacMode",
            "value",
            {"type": "adchlsDACMode", "adchlsDACMode": "simultaneous"},
        )

    @pytest.mark.asyncio
    async def test_set_rca_delay_clamped(self, api):
        api.async_set_data = AsyncMock(return_value=True)
        await api.async_set_rca_delay(999)
        call_args = api.async_set_data.call_args
        assert call_args[0][2]["i32_"] == 500  # clamped

    @pytest.mark.asyncio
    async def test_set_rca_delay_clamped_low(self, api):
        api.async_set_data = AsyncMock(return_value=True)
        await api.async_set_rca_delay(-10)
        call_args = api.async_set_data.call_args
        assert call_args[0][2]["i32_"] == 0  # clamped

    @pytest.mark.asyncio
    async def test_set_rca_fixed_volume(self, api):
        api.async_set_data = AsyncMock(return_value=True)
        await api.async_set_rca_fixed_volume(True)
        api.async_set_data.assert_called_once_with(
            "settings:/adchls/fixedVolume",
            "value",
            {"type": "bool_", "bool_": True},
        )

    @pytest.mark.asyncio
    async def test_set_knob_brightness_clamped(self, api):
        api.async_set_data = AsyncMock(return_value=True)
        await api.async_set_knob_brightness(150)
        call_args = api.async_set_data.call_args
        assert call_args[0][2]["i32_"] == 100  # clamped

    @pytest.mark.asyncio
    async def test_set_volume_clamped(self, api):
        api.async_set_data = AsyncMock(return_value=True)
        await api.async_set_volume(120)
        call_args = api.async_set_data.call_args
        assert call_args[0][2]["i32_"] == 100  # clamped

    @pytest.mark.asyncio
    async def test_set_mute(self, api):
        api.async_set_data = AsyncMock(return_value=True)
        await api.async_set_mute(True)
        api.async_set_data.assert_called_once_with(
            "settings:/mediaPlayer/mute",
            "value",
            {"type": "bool_", "bool_": True},
        )

    @pytest.mark.asyncio
    async def test_set_autoplay(self, api):
        api.async_set_data = AsyncMock(return_value=True)
        await api.async_set_autoplay(False)
        api.async_set_data.assert_called_once_with(
            "settings:/victrola/autoplay",
            "value",
            {"type": "bool_", "bool_": False},
        )

    @pytest.mark.asyncio
    async def test_set_source_enabled_valid(self, api):
        api.async_set_data = AsyncMock(return_value=True)
        result = await api.async_set_source_enabled("sonos", True)
        assert result is True
        api.async_set_data.assert_called_once_with(
            "settings:/victrola/sonosEnabled",
            "value",
            {"type": "bool_", "bool_": True},
        )

    @pytest.mark.asyncio
    async def test_set_source_enabled_unknown(self, api):
        api.async_set_data = AsyncMock(return_value=True)
        result = await api.async_set_source_enabled("invalid_source", True)
        assert result is False
        api.async_set_data.assert_not_called()

    @pytest.mark.asyncio
    async def test_quickplay(self, api):
        api.async_set_data = AsyncMock(return_value=True)
        result = await api.async_quickplay("victrolaQuickplaySonos", "spk-123")
        assert result is True
        api.async_set_data.assert_called_once_with(
            "victrola:ui/quickplay",
            "activate",
            {"type": "victrolaQuickplaySonos", "id": "spk-123"},
        )

    @pytest.mark.asyncio
    async def test_set_default_output(self, api):
        api.async_set_data = AsyncMock(return_value=True)
        result = await api.async_set_default_output("victrolaOutputSonos", "spk-123")
        assert result is True
        api.async_set_data.assert_called_once_with(
            "victrola:ui/setDefaultOutput",
            "activate",
            {"type": "victrolaOutputSonos", "id": "spk-123"},
        )

    @pytest.mark.asyncio
    async def test_select_speaker_combines_default_and_quickplay(self, api):
        api.async_set_data = AsyncMock(return_value=True)
        result = await api.async_select_speaker(
            "victrolaOutputSonos", "victrolaQuickplaySonos", "spk-123"
        )
        assert result is True
        assert api.async_set_data.call_count == 2

    @pytest.mark.asyncio
    async def test_reboot(self, api):
        api.async_set_data = AsyncMock(return_value=True)
        result = await api.async_reboot()
        assert result is True
        api.async_set_data.assert_called_once_with(
            "powermanager:goReboot",
            "activate",
            {"type": "bool_", "bool_": True},
        )
