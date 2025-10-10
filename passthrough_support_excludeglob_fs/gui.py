#!/usr/bin/env python3
"""GUI module for PassthroughFS using tkinter."""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import os
import threading
from typing import Optional
from .main import start_passthrough_fs, default_uid_and_gid, default_overwrite_rename_dest, default_symlink_creation_windows, default_rellinks, symlink_creation_windows_type
from typing import get_args


class PassthroughFSGUI:
    """GUI for PassthroughFS."""

    def __init__(self, root):
        self.root = root
        self.root.title("PassthroughFS")
        self.root.geometry("700x600")
        
        # Process tracking
        self.fs_thread: Optional[threading.Thread] = None
        self.is_running = False
        
        # Create main container
        main_frame = ttk.Frame(root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        root.columnconfigure(0, weight=1)
        root.rowconfigure(0, weight=1)
        
        # Title
        title_label = ttk.Label(main_frame, text="PassthroughFS Configuration", font=("", 14, "bold"))
        title_label.grid(row=0, column=0, columnspan=3, pady=(0, 10))
        
        current_row = 1
        
        # ===== Main Options Section =====
        main_section_label = ttk.Label(main_frame, text="Main Options", font=("", 12, "bold"))
        main_section_label.grid(row=current_row, column=0, columnspan=3, sticky=tk.W, pady=(10, 5))
        current_row += 1
        
        # Mountpoint
        ttk.Label(main_frame, text="Mountpoint:").grid(row=current_row, column=0, sticky=tk.W, pady=5)
        self.mountpoint_var = tk.StringVar()
        mountpoint_entry = ttk.Entry(main_frame, textvariable=self.mountpoint_var, width=40)
        mountpoint_entry.grid(row=current_row, column=1, sticky=(tk.W, tk.E), pady=5)
        ttk.Button(main_frame, text="Browse...", command=self.browse_mountpoint).grid(row=current_row, column=2, padx=5, pady=5)
        current_row += 1
        
        # Root directory
        ttk.Label(main_frame, text="Root Directory:").grid(row=current_row, column=0, sticky=tk.W, pady=5)
        self.root_var = tk.StringVar()
        root_entry = ttk.Entry(main_frame, textvariable=self.root_var, width=40)
        root_entry.grid(row=current_row, column=1, sticky=(tk.W, tk.E), pady=5)
        ttk.Button(main_frame, text="Browse...", command=self.browse_root).grid(row=current_row, column=2, padx=5, pady=5)
        current_row += 1
        
        # Patterns (exclude patterns)
        ttk.Label(main_frame, text="Exclude Patterns:").grid(row=current_row, column=0, sticky=tk.W, pady=5)
        self.patterns_var = tk.StringVar()
        patterns_entry = ttk.Entry(main_frame, textvariable=self.patterns_var, width=40)
        patterns_entry.grid(row=current_row, column=1, sticky=(tk.W, tk.E), pady=5, columnspan=2)
        ttk.Label(main_frame, text="(Separate with ':')").grid(row=current_row+1, column=1, sticky=tk.W, pady=(0, 5))
        current_row += 2
        
        # ===== Advanced Options Section (Collapsible) =====
        self.advanced_visible = tk.BooleanVar(value=False)
        advanced_frame = ttk.Frame(main_frame)
        advanced_frame.grid(row=current_row, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(10, 0))
        
        # Advanced toggle button
        self.advanced_toggle_btn = ttk.Button(
            advanced_frame, 
            text="▶ Show Advanced Options", 
            command=self.toggle_advanced
        )
        self.advanced_toggle_btn.grid(row=0, column=0, sticky=tk.W)
        current_row += 1
        
        # Advanced options container (initially hidden)
        self.advanced_container = ttk.Frame(main_frame)
        self.advanced_container.grid(row=current_row, column=0, columnspan=3, sticky=(tk.W, tk.E))
        self.advanced_container.grid_remove()  # Hide initially
        
        adv_row = 0
        
        # Cache directory
        ttk.Label(self.advanced_container, text="Cache Directory:").grid(row=adv_row, column=0, sticky=tk.W, pady=5)
        self.cache_dir_var = tk.StringVar()
        cache_entry = ttk.Entry(self.advanced_container, textvariable=self.cache_dir_var, width=40)
        cache_entry.grid(row=adv_row, column=1, sticky=(tk.W, tk.E), pady=5)
        ttk.Button(self.advanced_container, text="Browse...", command=self.browse_cache).grid(row=adv_row, column=2, padx=5, pady=5)
        ttk.Label(self.advanced_container, text="(Leave empty for default)").grid(row=adv_row+1, column=1, sticky=tk.W, pady=(0, 5))
        adv_row += 2
        
        # Boolean options
        self.debug_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(self.advanced_container, text="Enable Debug Mode", variable=self.debug_var).grid(row=adv_row, column=0, columnspan=2, sticky=tk.W, pady=5)
        adv_row += 1
        
        self.fusedebug_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(self.advanced_container, text="Enable FUSE Debug", variable=self.fusedebug_var).grid(row=adv_row, column=0, columnspan=2, sticky=tk.W, pady=5)
        adv_row += 1
        
        self.nothreads_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(self.advanced_container, text="Disable Multi-threading", variable=self.nothreads_var).grid(row=adv_row, column=0, columnspan=2, sticky=tk.W, pady=5)
        adv_row += 1
        
        self.overwrite_rename_dest_var = tk.BooleanVar(value=default_overwrite_rename_dest())
        ttk.Checkbutton(self.advanced_container, text="Overwrite Rename Destination", variable=self.overwrite_rename_dest_var).grid(row=adv_row, column=0, columnspan=2, sticky=tk.W, pady=5)
        adv_row += 1
        
        self.log_in_console_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(self.advanced_container, text="Log to Console", variable=self.log_in_console_var).grid(row=adv_row, column=0, columnspan=2, sticky=tk.W, pady=5)
        adv_row += 1
        
        self.log_in_syslog_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(self.advanced_container, text="Log to Syslog", variable=self.log_in_syslog_var).grid(row=adv_row, column=0, columnspan=2, sticky=tk.W, pady=5)
        adv_row += 1
        
        self.rellinks_var = tk.BooleanVar(value=default_rellinks())
        ttk.Checkbutton(self.advanced_container, text="Use Relative Links", variable=self.rellinks_var).grid(row=adv_row, column=0, columnspan=2, sticky=tk.W, pady=5)
        adv_row += 1
        
        # Log file
        ttk.Label(self.advanced_container, text="Log File:").grid(row=adv_row, column=0, sticky=tk.W, pady=5)
        self.log_file_var = tk.StringVar()
        log_file_entry = ttk.Entry(self.advanced_container, textvariable=self.log_file_var, width=40)
        log_file_entry.grid(row=adv_row, column=1, sticky=(tk.W, tk.E), pady=5)
        ttk.Button(self.advanced_container, text="Browse...", command=self.browse_log_file).grid(row=adv_row, column=2, padx=5, pady=5)
        adv_row += 1
        
        # UID/GID (only on Unix-like systems)
        if os.name != 'nt':
            ttk.Label(self.advanced_container, text="UID:").grid(row=adv_row, column=0, sticky=tk.W, pady=5)
            self.uid_var = tk.StringVar(value=str(default_uid_and_gid()[0]))
            ttk.Entry(self.advanced_container, textvariable=self.uid_var, width=20).grid(row=adv_row, column=1, sticky=tk.W, pady=5)
            adv_row += 1
            
            ttk.Label(self.advanced_container, text="GID:").grid(row=adv_row, column=0, sticky=tk.W, pady=5)
            self.gid_var = tk.StringVar(value=str(default_uid_and_gid()[1]))
            ttk.Entry(self.advanced_container, textvariable=self.gid_var, width=20).grid(row=adv_row, column=1, sticky=tk.W, pady=5)
            adv_row += 1
        else:
            self.uid_var = tk.StringVar(value="-1")
            self.gid_var = tk.StringVar(value="-1")
        
        # Symlink creation on Windows
        if os.name == 'nt':
            ttk.Label(self.advanced_container, text="Symlink Creation:").grid(row=adv_row, column=0, sticky=tk.W, pady=5)
            self.symlink_creation_var = tk.StringVar(value=default_symlink_creation_windows())
            symlink_options = get_args(symlink_creation_windows_type)
            symlink_combo = ttk.Combobox(self.advanced_container, textvariable=self.symlink_creation_var, values=symlink_options, state='readonly', width=20)
            symlink_combo.grid(row=adv_row, column=1, sticky=tk.W, pady=5)
            adv_row += 1
        else:
            self.symlink_creation_var = tk.StringVar(value='error')
        
        current_row += 1
        
        # ===== Control Buttons =====
        control_frame = ttk.Frame(main_frame)
        control_frame.grid(row=current_row, column=0, columnspan=3, pady=(20, 10))
        
        self.start_btn = ttk.Button(control_frame, text="Start", command=self.start_fs, width=15)
        self.start_btn.grid(row=0, column=0, padx=5)
        
        self.stop_btn = ttk.Button(control_frame, text="Stop", command=self.stop_fs, width=15, state=tk.DISABLED)
        self.stop_btn.grid(row=0, column=1, padx=5)
        
        current_row += 1
        
        # ===== Status Section =====
        status_label = ttk.Label(main_frame, text="Status:", font=("", 10, "bold"))
        status_label.grid(row=current_row, column=0, sticky=tk.W, pady=(10, 5))
        current_row += 1
        
        self.status_text = scrolledtext.ScrolledText(main_frame, height=8, width=70, state=tk.DISABLED)
        self.status_text.grid(row=current_row, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), pady=5)
        main_frame.rowconfigure(current_row, weight=1)
        
        # Configure column weights
        main_frame.columnconfigure(1, weight=1)
        
        self.log_status("Ready. Configure options and click Start.")
        
    def toggle_advanced(self):
        """Toggle visibility of advanced options."""
        if self.advanced_visible.get():
            self.advanced_container.grid_remove()
            self.advanced_toggle_btn.config(text="▶ Show Advanced Options")
            self.advanced_visible.set(False)
        else:
            self.advanced_container.grid()
            self.advanced_toggle_btn.config(text="▼ Hide Advanced Options")
            self.advanced_visible.set(True)
    
    def browse_mountpoint(self):
        """Open dialog to select mountpoint directory."""
        directory = filedialog.askdirectory(title="Select Mountpoint Directory")
        if directory:
            self.mountpoint_var.set(directory)
    
    def browse_root(self):
        """Open dialog to select root directory."""
        directory = filedialog.askdirectory(title="Select Root Directory")
        if directory:
            self.root_var.set(directory)
    
    def browse_cache(self):
        """Open dialog to select cache directory."""
        directory = filedialog.askdirectory(title="Select Cache Directory")
        if directory:
            self.cache_dir_var.set(directory)
    
    def browse_log_file(self):
        """Open dialog to select log file."""
        filename = filedialog.asksaveasfilename(
            title="Select Log File",
            defaultextension=".log",
            filetypes=[("Log files", "*.log"), ("All files", "*.*")]
        )
        if filename:
            self.log_file_var.set(filename)
    
    def log_status(self, message):
        """Add a message to the status text area."""
        self.status_text.config(state=tk.NORMAL)
        self.status_text.insert(tk.END, message + "\n")
        self.status_text.see(tk.END)
        self.status_text.config(state=tk.DISABLED)
    
    def validate_inputs(self):
        """Validate user inputs."""
        if not self.mountpoint_var.get():
            messagebox.showerror("Validation Error", "Mountpoint is required.")
            return False
        
        if not self.root_var.get():
            messagebox.showerror("Validation Error", "Root directory is required.")
            return False
        
        if not os.path.exists(self.root_var.get()):
            messagebox.showerror("Validation Error", "Root directory does not exist.")
            return False
        
        # Validate UID/GID if provided
        if os.name != 'nt':
            try:
                int(self.uid_var.get())
                int(self.gid_var.get())
            except ValueError:
                messagebox.showerror("Validation Error", "UID and GID must be integers.")
                return False
        
        return True
    
    def start_fs(self):
        """Start the filesystem."""
        if self.is_running:
            messagebox.showwarning("Already Running", "Filesystem is already running.")
            return
        
        if not self.validate_inputs():
            return
        
        # Gather parameters
        mountpoint = self.mountpoint_var.get()
        root = self.root_var.get()
        
        # Parse patterns
        patterns_str = self.patterns_var.get().strip()
        patterns = [p.strip() for p in patterns_str.split(':') if p.strip()] if patterns_str else None
        
        cache_dir = self.cache_dir_var.get().strip() or None
        
        uid = int(self.uid_var.get())
        gid = int(self.gid_var.get())
        
        debug = self.debug_var.get()
        fusedebug = self.fusedebug_var.get()
        nothreads = self.nothreads_var.get()
        overwrite_rename_dest = self.overwrite_rename_dest_var.get()
        log_in_console = self.log_in_console_var.get()
        log_in_syslog = self.log_in_syslog_var.get()
        rellinks = self.rellinks_var.get()
        
        log_file = self.log_file_var.get().strip() or None
        
        symlink_creation_windows = self.symlink_creation_var.get()
        
        # Log configuration
        self.log_status("=" * 50)
        self.log_status("Starting PassthroughFS with configuration:")
        self.log_status(f"  Mountpoint: {mountpoint}")
        self.log_status(f"  Root: {root}")
        if patterns:
            self.log_status(f"  Patterns: {patterns}")
        if cache_dir:
            self.log_status(f"  Cache: {cache_dir}")
        self.log_status("=" * 50)
        
        # Start filesystem in a separate thread
        def run_fs():
            try:
                # Note: foreground=True will block, so we can't use it in GUI
                # We'll use foreground=False but this may not work on all systems
                start_passthrough_fs(
                    mountpoint=mountpoint,
                    root=root,
                    patterns=patterns,
                    cache_dir=cache_dir,
                    uid=uid,
                    gid=gid,
                    foreground=True,  # This blocks, which is what we want in the thread
                    nothreads=nothreads,
                    fusedebug=fusedebug,
                    overwrite_rename_dest=overwrite_rename_dest,
                    debug=debug,
                    log_in_file=log_file,
                    log_in_console=log_in_console,
                    log_in_syslog=log_in_syslog,
                    symlink_creation_windows=symlink_creation_windows,
                    rellinks=rellinks
                )
            except Exception as e:
                self.root.after(0, lambda: self.log_status(f"Error: {str(e)}"))
                self.root.after(0, self.on_fs_stopped)
        
        self.fs_thread = threading.Thread(target=run_fs, daemon=True)
        self.fs_thread.start()
        
        self.is_running = True
        self.start_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)
        self.log_status("Filesystem started.")
    
    def stop_fs(self):
        """Stop the filesystem."""
        if not self.is_running:
            messagebox.showwarning("Not Running", "Filesystem is not running.")
            return
        
        # Attempt to unmount
        mountpoint = self.mountpoint_var.get()
        self.log_status(f"Attempting to unmount {mountpoint}...")
        
        try:
            if os.name == 'nt':
                # On Windows, we can't easily unmount via command
                self.log_status("Please unmount manually on Windows or close the application.")
            else:
                # On Unix-like systems, use fusermount
                import subprocess
                result = subprocess.run(['fusermount', '-u', mountpoint], capture_output=True, text=True)
                if result.returncode == 0:
                    self.log_status("Filesystem unmounted successfully.")
                else:
                    self.log_status(f"Unmount error: {result.stderr}")
        except Exception as e:
            self.log_status(f"Error during unmount: {str(e)}")
        
        self.on_fs_stopped()
    
    def on_fs_stopped(self):
        """Called when filesystem stops."""
        self.is_running = False
        self.start_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)
        self.log_status("Filesystem stopped.")


def launch_gui():
    """Launch the GUI application."""
    root = tk.Tk()
    app = PassthroughFSGUI(root)
    root.mainloop()
