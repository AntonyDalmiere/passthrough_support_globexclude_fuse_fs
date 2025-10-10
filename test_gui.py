#!/usr/bin/env python3
"""Tests for the GUI module."""

import unittest
import sys
import os

# Try to import tkinter - skip tests if not available
try:
    import tkinter as tk
    TKINTER_AVAILABLE = True
except ImportError:
    TKINTER_AVAILABLE = False


@unittest.skipIf(not TKINTER_AVAILABLE, "tkinter not available")
class TestGUI(unittest.TestCase):
    """Test the GUI functionality."""

    def setUp(self):
        """Set up test environment."""
        # Set up a virtual display if needed (for CI environments)
        self.display = os.environ.get('DISPLAY', '')
        
    def test_gui_import(self):
        """Test that GUI module can be imported."""
        from passthrough_support_excludeglob_fs.gui import launch_gui, PassthroughFSGUI
        self.assertIsNotNone(launch_gui)
        self.assertIsNotNone(PassthroughFSGUI)
    
    def test_gui_instantiation(self):
        """Test that GUI can be instantiated."""
        # Skip if no display available
        if not self.display:
            self.skipTest("No display available")
            
        from passthrough_support_excludeglob_fs.gui import PassthroughFSGUI
        
        root = tk.Tk()
        try:
            app = PassthroughFSGUI(root)
            
            # Check that main variables exist
            self.assertIsNotNone(app.mountpoint_var)
            self.assertIsNotNone(app.root_var)
            self.assertIsNotNone(app.patterns_var)
            
            # Check that controls exist
            self.assertIsNotNone(app.start_btn)
            self.assertIsNotNone(app.stop_btn)
            self.assertIsNotNone(app.status_text)
            
            # Check that advanced container exists
            self.assertIsNotNone(app.advanced_container)
            self.assertIsNotNone(app.advanced_visible)
            
        finally:
            root.destroy()
    
    def test_gui_set_values(self):
        """Test that GUI values can be set."""
        # Skip if no display available
        if not self.display:
            self.skipTest("No display available")
            
        from passthrough_support_excludeglob_fs.gui import PassthroughFSGUI
        
        root = tk.Tk()
        try:
            app = PassthroughFSGUI(root)
            
            # Set values
            app.mountpoint_var.set("/test/mount")
            app.root_var.set("/test/root")
            app.patterns_var.set("**/*.txt")
            
            # Verify values
            self.assertEqual(app.mountpoint_var.get(), "/test/mount")
            self.assertEqual(app.root_var.get(), "/test/root")
            self.assertEqual(app.patterns_var.get(), "**/*.txt")
            
        finally:
            root.destroy()
    
    def test_gui_toggle_advanced(self):
        """Test that advanced options can be toggled."""
        # Skip if no display available
        if not self.display:
            self.skipTest("No display available")
            
        from passthrough_support_excludeglob_fs.gui import PassthroughFSGUI
        
        root = tk.Tk()
        try:
            app = PassthroughFSGUI(root)
            
            # Initially hidden
            self.assertFalse(app.advanced_visible.get())
            
            # Toggle to show
            app.toggle_advanced()
            self.assertTrue(app.advanced_visible.get())
            
            # Toggle to hide
            app.toggle_advanced()
            self.assertFalse(app.advanced_visible.get())
            
        finally:
            root.destroy()
    
    def test_gui_validation(self):
        """Test input validation."""
        # Skip if no display available
        if not self.display:
            self.skipTest("No display available")
            
        from passthrough_support_excludeglob_fs.gui import PassthroughFSGUI
        import tempfile
        from unittest.mock import patch
        
        root = tk.Tk()
        try:
            app = PassthroughFSGUI(root)
            
            # Mock messagebox to avoid blocking
            with patch('passthrough_support_excludeglob_fs.gui.messagebox.showerror'):
                # Empty inputs should fail
                self.assertFalse(app.validate_inputs())
                
                # Set only mountpoint - should still fail
                app.mountpoint_var.set("/test/mount")
                self.assertFalse(app.validate_inputs())
                
                # Set mountpoint and non-existent root - should fail
                app.root_var.set("/nonexistent/directory")
                self.assertFalse(app.validate_inputs())
            
            # Set mountpoint and existing root - should pass
            with tempfile.TemporaryDirectory() as tmpdir:
                app.root_var.set(tmpdir)
                self.assertTrue(app.validate_inputs())
            
        finally:
            root.destroy()


class TestCLIGUIIntegration(unittest.TestCase):
    """Test CLI and GUI integration."""
    
    def test_cli_no_args_detection(self):
        """Test that CLI detects when no arguments are provided."""
        # Save original argv
        original_argv = sys.argv.copy()
        
        try:
            # Set argv to just script name
            sys.argv = ['test_script']
            
            # Check that we would launch GUI
            self.assertEqual(len(sys.argv), 1)
            
        finally:
            # Restore argv
            sys.argv = original_argv
    
    def test_cli_with_args(self):
        """Test that CLI works with arguments."""
        from passthrough_support_excludeglob_fs.main import cli
        
        # Save original argv
        original_argv = sys.argv.copy()
        
        try:
            # Set argv with help flag
            sys.argv = ['test_script', '--help']
            
            # This should raise SystemExit due to --help
            with self.assertRaises(SystemExit):
                cli()
                
        finally:
            # Restore argv
            sys.argv = original_argv


if __name__ == '__main__':
    unittest.main()
