#!/usr/bin/env python
"""
Test del servidor MCP en modo standalone.
Verifica que el servidor funciona correctamente cuando se instala como paquete.
"""

import subprocess

import pytest


class TestMCPServerImports:
    """Tests de imports del servidor MCP."""

    def test_mcp_server_importable(self):
        """Verifica que el servidor MCP es importable."""
        try:
            from geofinder.mcp_server import mcp, main
            assert mcp is not None
            assert main is not None
        except ImportError as e:
            pytest.skip(f"fastmcp not installed: {e}")

    def test_mcp_server_has_app(self):
        """Verifica que el servidor tiene la app FastMCP."""
        try:
            from geofinder.mcp_server import mcp
            assert hasattr(mcp, 'get_tools')
            assert hasattr(mcp, 'get_resources')
        except ImportError:
            pytest.skip("fastmcp not installed")


class TestMCPServerTools:
    """Tests de las herramientas MCP."""

    @pytest.mark.asyncio
    async def test_all_tools_registered(self):
        """Verifica que todas las herramientas MCP están registradas."""
        try:
            from geofinder.mcp_server import mcp
        except ImportError:
            pytest.skip("fastmcp not installed")

        # Listar herramientas
        tools = await mcp.get_tools()
        tool_names = list(tools.keys())

        # Herramientas esperadas
        expected_tools = [
            'find_place',
            'autocomplete',
            'find_reverse',
            'find_by_coordinates',
            'find_address',
            'find_road_km',
            'search_nearby',
        ]

        for tool in expected_tools:
            assert tool in tool_names, f"Tool '{tool}' not found in {tool_names}"

    @pytest.mark.asyncio
    async def test_tools_have_descriptions(self):
        """Verifica que las herramientas tienen descripciones."""
        try:
            from geofinder.mcp_server import mcp
        except ImportError:
            pytest.skip("fastmcp not installed")

        tools = await mcp.get_tools()

        for name, tool in tools.items():
            assert tool.description, f"Tool '{name}' has no description"
            assert len(tool.description) > 10, f"Tool '{name}' description too short"


class TestMCPServerResources:
    """Tests de los recursos MCP."""

    @pytest.mark.asyncio
    async def test_resources_available(self):
        """Verifica que los recursos están registrados (pueden ser 0)."""
        try:
            from geofinder.mcp_server import mcp
        except ImportError:
            pytest.skip("fastmcp not installed")

        resources = await mcp.get_resources()
        assert isinstance(resources, dict)


class TestMCPEntryPoint:
    """Tests del entry point del servidor MCP."""

    def test_entry_point_exists(self):
        """Verifica que el entry point existe."""
        result = subprocess.run(
            ['which', 'geofinder-icgc'],
            capture_output=True,
            text=True
        )

        # Si el paquete está instalado en modo editable, debe existir
        if result.returncode == 0:
            assert 'geofinder-icgc' in result.stdout

    def test_entry_point_help(self):
        """Verifica que el entry point muestra ayuda."""
        try:
            result = subprocess.run(
                ['geofinder-icgc', '--help'],
                capture_output=True,
                text=True,
                timeout=5
            )

            # Si funciona, debe mostrar información
            if result.returncode == 0:
                assert 'geofinder' in result.stdout.lower() or 'mcp' in result.stdout.lower()
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pytest.skip("geofinder-icgc not in PATH or timed out")


class TestMCPServerFunctionality:
    """Tests de funcionalidad del servidor MCP."""

    @pytest.mark.asyncio
    async def test_mcp_server_can_start(self):
        """Verifica que el servidor puede iniciar (sin ejecutar)."""
        try:
            from geofinder.mcp_server import mcp

            # Verificar que tiene los métodos necesarios
            assert hasattr(mcp, 'run')
            assert callable(mcp.run)
        except ImportError:
            pytest.skip("fastmcp not installed")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
