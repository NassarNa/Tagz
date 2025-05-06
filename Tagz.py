#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue May 06 21:39:00 2025

@author: nasimnassar
"""

import os
import json
import re
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageTk
import pygame
import threading
from datetime import datetime
import configparser
import subprocess
from humanize import naturalsize
from mutagen.mp3 import MP3
from mutagen.mp4 import MP4
import tempfile
import io

# Configuration file
CONFIG_FILE = "tagz_config.ini"
TAG_FILE = "tags.json"

def list_files(directory):
    """Returns a sorted list of files in the directory with metadata."""
    if not os.path.isdir(directory):
        return []
    
    files = []
    for file_name in os.listdir(directory):
        file_path = os.path.join(directory, file_name)
        if os.path.isfile(file_path):
            name, ext = os.path.splitext(file_name)
            size = os.path.getsize(file_path)
            file_type = get_file_type(file_name)
            
            file_info = {
                "name": file_name,
                "basename": name,
                "path": file_path,
                "ext": ext.lower(),
                "size": size,
                "human_size": naturalsize(size),
                "type": file_type,
                "length": 0,
                "modified": os.path.getmtime(file_path)
            }
            
            # Get length for media files
            if file_type in ["video", "audio"]:
                file_info["length"] = get_file_length(file_path)
                
            # Get tags
            file_info["tags"] = get_tags_for_file(file_path)
            
            files.append(file_info)
    
    return files

def get_file_type(file_name):
    """Determines file type based on the extension."""
    ext = file_name.lower()
    if ext.endswith((".mp4", ".mov", ".avi", ".mkv", ".webm", ".3gp", ".wmv", ".m4v", ".divx")):
        return "video"
    if ext.endswith((".mp3", ".wav", ".ogg", ".flac", ".m4a")):
        return "audio"
    if ext.endswith((".pdf", ".doc", ".docx", ".txt", ".rtf", ".xlsx", ".xls", ".json")):
        return "document"
    if ext.endswith((".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp")):
        return "image"
    if ext.endswith((".mobi", ".epub")):
        return "ebook"
    return "other"

def get_file_length(file_path):
    """Gets the duration of media files."""
    try:
        ext = os.path.splitext(file_path)[1].lower()
        
        if ext == ".mp3":
            return int(MP3(file_path).info.length)
        elif ext == ".m4a" or ext == ".mp4":
            return int(MP4(file_path).info.length)
        elif ext in [".avi", ".mkv", ".mov", ".webm"]:
            result = subprocess.run(
                ["ffprobe", "-i", file_path, "-show_entries", "format=duration",
                 "-v", "quiet", "-of", "csv=p=0"],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
            )
            return int(float(result.stdout.strip()))
    except Exception as e:
        print(f"Error getting length for {file_path}: {e}")
        return 0
    
    return 0

def format_length(seconds):
    """Formats media duration as HH:MM:SS."""
    if seconds <= 0:
        return "-"
    
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    
    if hours > 0:
        return f"{hours:02}:{minutes:02}:{secs:02}"
    else:
        return f"{minutes:02}:{secs:02}"

def add_tag_to_file(file_path, tag):
    """Adds a tag to a file and updates JSON storage."""
    if not tag.strip():
        return False
    
    # Update master tags file
    tags_data = {}
    if os.path.exists(TAG_FILE):
        with open(TAG_FILE, "r") as f:
            try:
                tags_data = json.load(f)
            except json.JSONDecodeError:
                tags_data = {}
    
    if file_path not in tags_data:
        tags_data[file_path] = []
    
    if tag not in tags_data[file_path]:
        tags_data[file_path].append(tag)
    
    with open(TAG_FILE, "w") as f:
        json.dump(tags_data, f, indent=4)
    
    # Update local tags file in the current directory
    local_tag_file = os.path.join(os.path.dirname(file_path), "local_tags.json")
    local_tags_data = {}
    
    if os.path.exists(local_tag_file):
        with open(local_tag_file, "r") as f:
            try:
                local_tags_data = json.load(f)
            except json.JSONDecodeError:
                local_tags_data = {}
    
    # Use relative path as key for local tags
    rel_path = os.path.basename(file_path)
    if rel_path not in local_tags_data:
        local_tags_data[rel_path] = []
    
    if tag not in local_tags_data[rel_path]:
        local_tags_data[rel_path].append(tag)
    
    with open(local_tag_file, "w") as f:
        json.dump(local_tags_data, f, indent=4)
    
    return True

def remove_tag_from_file(file_path, tag):
    """Removes a tag from a file and updates JSON storage."""
    updated = False
    
    # Update master tags file
    if os.path.exists(TAG_FILE):
        with open(TAG_FILE, "r") as f:
            try:
                tags_data = json.load(f)
            except json.JSONDecodeError:
                tags_data = {}
        
        if file_path in tags_data and tag in tags_data[file_path]:
            tags_data[file_path].remove(tag)
            updated = True
            
            if not tags_data[file_path]:
                tags_data.pop(file_path)
            
            with open(TAG_FILE, "w") as f:
                json.dump(tags_data, f, indent=4)
    
    # Update local tags file
    local_tag_file = os.path.join(os.path.dirname(file_path), "local_tags.json")
    if os.path.exists(local_tag_file):
        with open(local_tag_file, "r") as f:
            try:
                local_tags_data = json.load(f)
            except json.JSONDecodeError:
                local_tags_data = {}
        
        rel_path = os.path.basename(file_path)
        if rel_path in local_tags_data and tag in local_tags_data[rel_path]:
            local_tags_data[rel_path].remove(tag)
            updated = True
            
            if not local_tags_data[rel_path]:
                local_tags_data.pop(rel_path)
            
            with open(local_tag_file, "w") as f:
                json.dump(local_tags_data, f, indent=4)
    
    return updated

def get_tags_for_file(file_path):
    """Retrieves the tags for a given file from both master and local JSON files."""
    tags = []
    
    # Get tags from master file
    if os.path.exists(TAG_FILE):
        with open(TAG_FILE, "r") as f:
            try:
                master_tags = json.load(f).get(file_path, [])
                tags.extend(master_tags)
            except json.JSONDecodeError:
                pass
    
    # Get tags from local file
    local_tag_file = os.path.join(os.path.dirname(file_path), "local_tags.json")
    if os.path.exists(local_tag_file):
        with open(local_tag_file, "r") as f:
            try:
                rel_path = os.path.basename(file_path)
                local_tags = json.load(f).get(rel_path, [])
                # Add only unique tags
                for tag in local_tags:
                    if tag not in tags:
                        tags.append(tag)
            except json.JSONDecodeError:
                pass
    
    return tags

def generate_suggested_tags(filename):
    """Generates suggested tags based on the filename and optional directory."""
    name, ext = os.path.splitext(filename)
    suggested_tags = set()

    # Add the file extension as a tag (without the dot)
    if ext:
        suggested_tags.add(ext[1:].lower())

    # Split by common separators
    separators = [" ", "-", "_", ".", ",", ":", ";", "+", "&", "#", "=", "(", ")", "!", "?"]
    parts = [name]

    for separator in separators:
        new_parts = []
        for part in parts:
            new_parts.extend([p for p in part.split(separator) if p])
        parts = new_parts
    
    # Check for common date formats in the filename
    date_patterns = [
        r'\b\d{4}-\d{2}-\d{2}\b',  # YYYY-MM-DD
        r'\b\d{2}-\d{2}-\d{4}\b',  # DD-MM-YYYY or MM-DD-YYYY
        r'\b\d{8}\b',              # YYYYMMDD
        r'\d{8}',              # YYYYMMDD
        r'\b\d{2}\.\d{2}\.\d{4}\b',  # DD.MM.YYYY
        r'\b\d{4}\.\d{2}\.\d{2}\b',  # YYYY.MM.DD
        r'\b\d{2}_\d{2}_\d{4}\b',  # DD_MM_YYYY
        r'\b\d{4}_\d{2}_\d{2}\b',  # YYYY_MM_DD
        r'\d{2}_\d{2}_\d{4}',    # DD_MM_YYYY (no \b)
        r'\d{4}_\d{2}_\d{2}'    # YYYY_MM_DD (no \b)
    ]
    
    for pattern in date_patterns:
        dates = re.findall(pattern, name)
        for date in dates:
            suggested_tags.add(date)  # The recognized date as is
    
            # Add year, month, and day tags (where applicable)
            if len(date) == 8:  # YYYYMMDD or DDMMYYYY - ambiguous
                suggested_tags.add(date[0:4])  # Year (or first 4 digits)
                suggested_tags.add(date[4:8])  # Year (or last 4 digits)
            elif len(date) == 10:  # YYYY-MM-DD, DD-MM-YYYY, YYYY.MM.DD, DD.MM.YYYY, YYYY_MM_DD, DD_MM_YYYY
                 suggested_tags.add(date[0:4])  # Year (or first 4 digits)
                 suggested_tags.add(date[6:10])  # Year (or last 4 digits)
    
    # Look for year patterns (e.g., 2023, 2024)
    # Find years with word boundaries
    years_wb = re.findall(r'\b(19\d{2}|20\d{2})\b', name)
    for year in years_wb:
        suggested_tags.add(year)
    
    # Find years surrounded by non-word characters or string boundaries
    years_nb = re.findall(r'(?:^|\W)(19\d{2}|20\d{2})(?:$|\W)', name)
    for year in years_nb:
        suggested_tags.add(year)
    
    # Look for dimensions (e.g., 1920x1080)
    dimensions = re.findall(r'\b\d+[xX]\d+\b', name)
    for dim in dimensions:
        suggested_tags.add(dim)
        
    # Look for video resolutions (e.g., 240p, 360p, 480p, 720p, 1080p, etc.)
    resolutions = re.findall(r'\b(\d{3,4}p)\b', name, re.IGNORECASE)  # Case-insensitive
    for res in resolutions:
        suggested_tags.add(res.lower())
    resolutions2 = re.findall(r'(\d{3,4}p)', name, re.IGNORECASE)  # Case-insensitive
    for res2 in resolutions2:
        suggested_tags.add(res2.lower())

    # Add all significant parts as tags (minimal filtering)
    for part in parts:
        # Skip parts that are only one character long
        if len(part) > 1:
            suggested_tags.add(part.lower())

    return sorted(list(suggested_tags))

def get_all_tags():
    """Returns a list of all tags used in the system."""
    if not os.path.exists(TAG_FILE):
        return []
    
    with open(TAG_FILE, "r") as f:
        try:
            tags_data = json.load(f)
            all_tags = set()
            for file_tags in tags_data.values():
                all_tags.update(file_tags)
            return sorted(list(all_tags))
        except json.JSONDecodeError:
            return []

def search_files_by_tags(files, tags):
    """Filter files by tags."""
    if not tags:
        return files
    
    filtered_files = []
    for file in files:
        file_tags = set(file.get("tags", []))
        if all(tag in file_tags for tag in tags):
            filtered_files.append(file)
    
    return filtered_files

class TagzApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Tagz - File Tagging App")
        self.root.geometry("1200x800")
        self.root.minsize(900, 600)
        
        # Initialize audio player
        pygame.mixer.init()
        self.audio_playing = False
        self.current_audio = None
        
        # Load configuration
        self.config = configparser.ConfigParser()
        self.load_config()
        
        # Initialize variables
        self.current_directory = self.config.get("Settings", "last_directory", fallback=os.getcwd())
        self.recent_directories = self.get_recent_directories()
        self.files = []
        self.filtered_files = []
        self.current_file = None
        self.search_tags = []
        self.view_mode = tk.StringVar(value="local")  # Default to local
        
        # Apply a theme (e.g., 'clam', 'alt', 'default', 'classic', 'vista', 'xpams')
        s = ttk.Style()
        s.theme_use('clam')  # Try different themes
        # --- OR ---
        # Customize specific elements
        # s.configure('TLabel', background='lightgray', padding=5)
        # s.configure('TButton', padding=5, font=('Helvetica', 10))
        
        # Initialize UI
        self.init_ui()
        
        # Load files from last directory
        self.refresh_file_list()
    
    def load_config(self):
        """Load configuration from file."""
        if os.path.exists(CONFIG_FILE):
            self.config.read(CONFIG_FILE)
        
        if not self.config.has_section("Settings"):
            self.config.add_section("Settings")
        
        if not self.config.has_section("RecentDirectories"):
            self.config.add_section("RecentDirectories")
    
    def save_config(self):
        """Save configuration to file."""
        with open(CONFIG_FILE, "w") as f:
            self.config.write(f)
    
    def get_recent_directories(self):
        """Get list of recent directories from config."""
        if not self.config.has_section("RecentDirectories"):
            return []
        
        return [dir for _, dir in self.config.items("RecentDirectories")]
    
    def add_recent_directory(self, directory):
        """Add directory to recent list."""
        if not self.config.has_section("RecentDirectories"):
            self.config.add_section("RecentDirectories")
        
        # Remove if already exists
        for key, value in self.config.items("RecentDirectories"):
            if value == directory:
                self.config.remove_option("RecentDirectories", key)
        
        # Add to beginning (we use timestamps as keys for ordering)
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        self.config.set("RecentDirectories", timestamp, directory)
        
        # Keep only the 10 most recent
        items = list(self.config.items("RecentDirectories"))
        if len(items) > 10:
            items.sort(reverse=True)
            for key, _ in items[10:]:
                self.config.remove_option("RecentDirectories", key)
        
        self.recent_directories = self.get_recent_directories()
        self.directory_dropdown["values"] = self.recent_directories
    
    def init_ui(self):
        """Initializes the user interface."""
        # Create main layout frames
        self.top_frame = ttk.Frame(self.root)
        self.top_frame.pack(fill="x", pady=5, padx=10)
        
        self.middle_frame = tk.Frame(self.root)
        self.middle_frame.pack(fill="both", expand=True, pady=5, padx=10)
        
        self.bottom_frame = tk.Frame(self.root)
        self.bottom_frame.pack(fill="x", pady=5, padx=10)
        
        # Directory selection
        directory_frame = tk.Frame(self.top_frame)
        directory_frame.pack(fill="x")
        
        tk.Label(directory_frame, text="Directory:").pack(side="left", padx=5)
        
        self.directory_var = tk.StringVar(value=self.current_directory)
        self.directory_dropdown = ttk.Combobox(directory_frame, textvariable=self.directory_var, width=60)
        self.directory_dropdown["values"] = self.recent_directories
        self.directory_dropdown.pack(side="left", padx=5, fill="x", expand=True)
        self.directory_dropdown.bind("<Return>", lambda e: self.change_directory())
        
        tk.Button(directory_frame, text="Go", command=self.change_directory, bg="orange").pack(side="left", padx=5)
        tk.Button(directory_frame, text="Browse...", command=self.browse_directory, bg="orange").pack(side="left", padx=5)
        
        # Filter and search options
        filter_frame = tk.Frame(self.top_frame)
        filter_frame.pack(fill="x", pady=5)
        
        # Text filter
        tk.Label(filter_frame, text="Filter:").pack(side="left", padx=5)
        self.filter_var = tk.StringVar()
        self.filter_entry = tk.Entry(filter_frame, textvariable=self.filter_var)
        self.filter_entry.pack(side="left", padx=5, fill="x", expand=True)
        self.filter_entry.bind("<KeyRelease>", lambda e: self.apply_filters())
        
        # Tag filter
        tk.Label(filter_frame, text="Tag Filter:").pack(side="left", padx=5)
        self.tag_filter_var = tk.StringVar()
        self.tag_filter_combo = ttk.Combobox(filter_frame, textvariable=self.tag_filter_var, width=15)
        self.tag_filter_combo.pack(side="left", padx=5)
        self.update_tag_filter_combo()
        
        tk.Button(filter_frame, text="Add Tag Filter", command=self.add_tag_filter, bg="orange").pack(side="left", padx=5)
        tk.Button(filter_frame, text="Clear Filters", command=self.clear_filters, bg="orange").pack(side="left", padx=5)
        
        # Active tag filters display
        self.active_filters_frame = tk.Frame(self.top_frame)
        self.active_filters_frame.pack(fill="x", pady=5)
        self.update_active_filters_display()
        
        # Label for current directory / View Mode
        self.current_directory_label = ttk.Label(
            self.top_frame,
            # Initial text will be set by refresh_file_list
            text="Initializing...", 
            anchor=tk.W,
        )
        self.current_directory_label.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10)) # Add some padding

        # View Mode Radio Buttons
        view_mode_frame = ttk.Frame(self.top_frame) # Optional: Group radios
        view_mode_frame.pack(side=tk.LEFT)

        self.local_view_radio = ttk.Radiobutton(
            view_mode_frame, # Add to the group frame
            text="Local",
            variable=self.view_mode,
            value="local",
            command=self.refresh_file_list
        )
        self.local_view_radio.pack(side=tk.LEFT, padx=2)

        self.global_view_radio = ttk.Radiobutton(
            view_mode_frame, # Add to the group frame
            text="Global",
            variable=self.view_mode,
            value="global",
            command=self.refresh_file_list
        )
        self.global_view_radio.pack(side=tk.LEFT, padx=2)
        
        # Split middle frame for file list and preview
        self.middle_frame.columnconfigure(0, weight=3)
        self.middle_frame.columnconfigure(1, weight=2)
        self.middle_frame.rowconfigure(0, weight=1)
        
        # File list section
        file_list_frame = tk.Frame(self.middle_frame)
        file_list_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 5))
        
        # Button frame
        button_frame = tk.Frame(file_list_frame)
        button_frame.pack(pady=5)  # Add some padding

        tk.Button(button_frame, text="Select All", command=self.select_all_files, bg="yellow").pack(side="left", padx=5)
        tk.Button(button_frame, text="Select None", command=self.select_none_files, bg="yellow").pack(side="left", padx=5)
        tk.Button(button_frame, text="Select Similar", command=self.select_similar_files, bg="yellow").pack(side="left", padx=5)

        # Create the treeview with scrollbars
        self.create_file_tree(file_list_frame)
        
        # Preview section
        preview_frame = tk.LabelFrame(self.middle_frame, text="File Preview")
        preview_frame.grid(row=0, column=1, sticky="nsew", padx=(5, 0))
        
        self.preview_canvas = tk.Canvas(preview_frame, bg="white")
        self.preview_canvas.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Media controls if needed
        self.media_controls_frame = tk.Frame(preview_frame)
        self.media_controls_frame.pack(fill="x", padx=10, pady=5)
        
        self.play_button = tk.Button(self.media_controls_frame, text="▶ Play", command=self.toggle_media_playback)
        self.play_button.pack(side="left", padx=5)
        self.play_button.pack_forget()  # Hide initially
        
        # Tagging section
        tagging_frame = tk.LabelFrame(self.bottom_frame, text="Tagging")
        tagging_frame.pack(fill="x", pady=5)
        
        # Current file info
        self.file_info_var = tk.StringVar(value="No file selected")
        file_info_label = tk.Label(tagging_frame, textvariable=self.file_info_var)
        file_info_label.pack(fill="x", padx=10, pady=5)
        
        # Open Containing Folder Button
        self.open_folder_button = tk.Button(
            tagging_frame, text="Open Folder", command=self.open_containing_folder, bg="yellow"
        )
        self.open_folder_button.pack(side="right", padx=5)
        
        # Toggle button for full path tags
        self.full_path_tags_var = tk.BooleanVar(value=False)  # Default: last folder only
        full_path_tags_toggle = ttk.Checkbutton(
            tagging_frame,
            text="Full Path Tags",
            variable=self.full_path_tags_var
        )
        full_path_tags_toggle.pack(side="right", padx=5)
        
        # Tags of the current file
        self.current_tags_frame = tk.Frame(tagging_frame)
        self.current_tags_frame.pack(fill="x", padx=10, pady=5)
        self.current_tags_frame.config(bg="darkgreen")
        
        # Add tag section
        add_tag_frame = tk.Frame(tagging_frame)
        add_tag_frame.pack(fill="x", padx=10, pady=5)

        tk.Label(add_tag_frame, text="Add Tag to Selected:").pack(side="left", padx=5)
        self.tag_entry_var = tk.StringVar()
        self.tag_entry = tk.Entry(add_tag_frame, textvariable=self.tag_entry_var, width=20)
        self.tag_entry.pack(side="left", padx=5, fill="x", expand=True)
        self.tag_entry.bind("<Return>", lambda e: self.add_tag_to_selected()) # Changed function call

        tk.Button(add_tag_frame, text="Add Tag", command=self.add_tag_to_selected, bg="yellow").pack(side="left", padx=5) # Changed function call
        tk.Button(add_tag_frame, text="Remove Tag from Selected", command=self.remove_tag_from_selected, bg="yellow").pack(side="left", padx=5) # Added remove button

        # Suggested tags section
        suggested_frame = tk.LabelFrame(tagging_frame, text="Suggested Tags", bg="lightgreen")
        suggested_frame.pack(fill="x", padx=10, pady=5)
        
        self.suggested_tags_frame = tk.Frame(suggested_frame, bg="lightgreen")
        self.suggested_tags_frame.pack(fill="x", padx=5, pady=5)
        
        # Popular tags section
        popular_frame = tk.LabelFrame(tagging_frame, text="Popular Tags")
        popular_frame.pack(fill="x", padx=10, pady=5)
        
        self.popular_tags_frame = tk.Frame(popular_frame, bg="lightblue")
        self.popular_tags_frame.pack(fill="x", padx=5, pady=5)
        
        # Update the popular tags
        self.update_popular_tags()
        self.update_tag_filter_combo()
        self.update_active_filters_display()
    
    def select_all_files(self):
        """Selects all files in the treeview."""
        self.file_tree.selection_set(self.file_tree.get_children())

    def select_none_files(self):
        """Deselects all files in the treeview."""
        self.file_tree.selection_set()

    def select_similar_files(self):
        """Selects files with the same extension as the first selected file."""

        selected_items = self.file_tree.selection()
        if not selected_items:
            return

        first_item = selected_items[0]
        first_file_path = self.file_tree.item(first_item, 'tags')[0]
        _, first_ext = os.path.splitext(first_file_path)
        
        similar_items = []
        for item in self.file_tree.get_children():
            file_path = self.file_tree.item(item, 'tags')[0]
            _, ext = os.path.splitext(file_path)
            if ext.lower() == first_ext.lower():
                similar_items.append(item)
        
        self.file_tree.selection_set(similar_items)
    
    def add_tag_to_selected(self):
        """Adds a tag to all selected files."""
        tag = self.tag_entry_var.get().strip()
        if not tag:
            return

        selected_items = self.file_tree.selection()
        if not selected_items:
            messagebox.showinfo("Info", "Please select one or more files.")
            return

        for item in selected_items:
            file_path = self.file_tree.item(item, 'tags')[0]
            for file in self.files: # Use self.files, not self.filtered_files
                if file["path"] == file_path:
                    if add_tag_to_file(file["path"], tag):
                        file["tags"].append(tag) # Update file object directly
        
        self.update_file_tree() # Refresh the tree to show updated tags
        self.update_current_tags()
        self.update_suggested_tags()
        self.update_popular_tags()
        self.update_tag_filter_combo()
        self.tag_entry_var.set("") # Clear entry

    def remove_tag_from_selected(self):
        """Removes a tag from all selected files."""

        tag = self.tag_entry_var.get().strip()
        if not tag:
            return

        selected_items = self.file_tree.selection()
        if not selected_items:
            messagebox.showinfo("Info", "Please select one or more files.")
            return

        for item in selected_items:
            file_path = self.file_tree.item(item, 'tags')[0]
            for file in self.files: # Use self.files
                if file["path"] == file_path:
                    if remove_tag_from_file(file["path"], tag):
                        file["tags"] = [t for t in file["tags"] if t != tag] # Remove tag from list
        
        self.update_file_tree() # Refresh tree
        self.update_current_tags()
        self.update_suggested_tags()
        self.update_popular_tags()
        self.update_tag_filter_combo()
        self.tag_entry_var.set("")
    
    def create_file_tree(self, parent):
        """Creates the file treeview with scrollbars."""
        tree_frame = tk.Frame(parent)
        tree_frame.pack(fill="both", expand=True)
        
        # Scrollbars
        tree_scroll_y = ttk.Scrollbar(tree_frame)
        tree_scroll_y.pack(side="right", fill="y")
        
        tree_scroll_x = ttk.Scrollbar(tree_frame, orient="horizontal")
        tree_scroll_x.pack(side="bottom", fill="x")
        
        # Treeview
        self.file_tree = ttk.Treeview(
            tree_frame,
            columns=("Name", "Ext", "Type", "Size", "Length", "Modified", "Tags"),
            show="headings",
            yscrollcommand=tree_scroll_y.set,
            xscrollcommand=tree_scroll_x.set
        )
        
        # Configure columns
        column_configs = {
            "Name": {"width": 180, "anchor": "w"},
            "Ext": {"width": 50, "anchor": "center"},
            "Type": {"width": 80, "anchor": "center"},
            "Size": {"width": 80, "anchor": "e"},
            "Length": {"width": 80, "anchor": "center"},
            "Modified": {"width": 150, "anchor": "center"},
            "Tags": {"width": 200, "anchor": "w"},
        }
        
        for col, config in column_configs.items():
            self.file_tree.heading(col, text=col, command=lambda c=col: self.sort_by_column(c))
            self.file_tree.column(col, width=config["width"], anchor=config["anchor"])
        
        # Pack the treeview
        self.file_tree.pack(fill="both", expand=True)
        
        # Configure scrollbars
        tree_scroll_y.config(command=self.file_tree.yview)
        tree_scroll_x.config(command=self.file_tree.xview)
        
        # Bind events
        self.file_tree.bind("<ButtonRelease-1>", self.on_file_select)
        self.file_tree.bind("<Double-1>", self.open_file)
        
        # Track sort order
        self.sort_column = "Name"
        self.sort_ascending = True
    
    def browse_directory(self):
        """Opens a dialog to select a directory."""
        directory = filedialog.askdirectory(initialdir=self.current_directory)
        if directory:
            self.current_directory = directory
            self.directory_var.set(directory)
            self.config.set("Settings", "last_directory", directory)
            self.add_recent_directory(directory)
            self.save_config()
            self.refresh_file_list()
    
    def change_directory(self):
        """Change to the directory entered in the combobox."""
        directory = self.directory_var.get()
        if os.path.isdir(directory):
            self.current_directory = directory
            self.config.set("Settings", "last_directory", directory)
            self.add_recent_directory(directory)
            self.save_config()
            self.refresh_file_list()
        else:
            messagebox.showerror("Error", f"Directory does not exist: {directory}")
    
    def refresh_file_list(self):
        """Refreshes the file list based on the current directory or global view."""
        # Stop preview before refreshing list
        self.stop_media_playback()
        self.preview_canvas.delete("all")
        self.current_file = None
        self.update_file_info()
        self.update_current_tags()
        self.update_suggested_tags()

        if self.view_mode.get() == "local":
            # Ensure current_directory is valid before listing
            if not os.path.isdir(self.current_directory):
                messagebox.showerror("Error", f"Directory does not exist: {self.current_directory}")
                # Optionally, revert to a default directory or clear the list
                self.files = []
                self.current_directory = os.getcwd() # Revert to CWD
                self.directory_var.set(self.current_directory)
                self.current_directory_label.config(text=f"Directory: {self.current_directory}")
            else:
                 self.files = list_files(self.current_directory)
                 self.current_directory_label.config(
                    text=f"Directory: {self.current_directory}"
                 )
        elif self.view_mode.get() == "global":
            self.files = self.load_global_files()
            # Add 'Directory' column if not already present in global load
            if self.files and "directory" not in self.files[0]:
                 for file_info in self.files:
                     file_info["directory"] = os.path.dirname(file_info["path"])

            # Make sure 'Directory' column exists in treeview for global view
            # This might require adjusting create_file_tree if you want to show it
            self.current_directory_label.config(text="View: Global Tags")

        # Apply filters (which includes sorting and updating the tree)
        self.apply_filters() # This now calls update_file_tree

        # Update other UI elements that depend on the list
        self.update_tag_filter_combo()
        self.update_popular_tags() # Refresh popular tags based on potential new global tags

        # Optionally select the first item
        children = self.file_tree.get_children()
        if children:
            self.file_tree.selection_set(children[0])
            self.file_tree.focus(children[0])
            # Trigger selection event manually to load preview etc.
            self.on_file_select(None) # Pass None as event argument
        else:
             # Clear preview and details if list is empty
            self.preview_canvas.delete("all")
            self.file_info_var.set("No files found")
            self.update_current_tags() # Clear tags display
            self.update_suggested_tags() # Clear suggestions
    
    def apply_filters(self):
        """Apply all filters to the file list."""
        # Start with all files
        filtered_files = self.files
        
        # Apply text filter
        filter_text = self.filter_var.get().lower()
        if filter_text:
            filtered_files = [file for file in filtered_files 
                             if filter_text in file["name"].lower()]
        
        # Apply tag filters
        if self.search_tags:
            filtered_files = search_files_by_tags(filtered_files, self.search_tags)
        
        # Update the display
        self.filtered_files = filtered_files
        self.update_file_tree()
    
    def update_file_tree(self):
        """Updates the file tree with the current filtered list."""
        # Clear the tree
        self.file_tree.delete(*self.file_tree.get_children())
        
        # Sort the files
        self.sort_files()
        
        # Add files to the tree
        for file in self.filtered_files:
            # Format modified date
            modified_date = datetime.fromtimestamp(file["modified"]).strftime("%Y-%m-%d %H:%M")
            
            # Format tags
            tags_str = ", ".join(file["tags"]) if file["tags"] else ""
            
            # Format length
            length_str = format_length(file["length"]) if file["length"] > 0 else "-"
            
            # Extract extension without dot
            ext = file["ext"][1:] if file["ext"] else ""
            
            # Insert into tree
            self.file_tree.insert(
                "", "end", 
                values=(
                    file["basename"],
                    ext,
                    file["type"].capitalize(),
                    file["human_size"],
                    length_str,
                    modified_date,
                    tags_str
                ),
                tags=(file["path"],)#,
            )
    
    def sort_files(self):
        """Sort the filtered files based on current sort column."""
        reverse = not self.sort_ascending
        
        if self.sort_column == "Name":
            self.filtered_files.sort(key=lambda x: x["basename"].lower(), reverse=reverse)
        elif self.sort_column == "Ext":
            self.filtered_files.sort(key=lambda x: x["ext"].lower(), reverse=reverse)
        elif self.sort_column == "Type":
            self.filtered_files.sort(key=lambda x: x["type"], reverse=reverse)
        elif self.sort_column == "Size":
            self.filtered_files.sort(key=lambda x: x["size"], reverse=reverse)
        elif self.sort_column == "Length":
            self.filtered_files.sort(key=lambda x: x["length"], reverse=reverse)
        elif self.sort_column == "Modified":
            self.filtered_files.sort(key=lambda x: x["modified"], reverse=reverse)
        elif self.sort_column == "Tags":
            self.filtered_files.sort(key=lambda x: len(x["tags"]), reverse=reverse)
    
    def sort_by_column(self, column):
        """Sorts the treeview by the specified column."""
        if self.sort_column == column:
            # Toggle sort direction
            self.sort_ascending = not self.sort_ascending
        else:
            # New column, default to ascending
            self.sort_column = column
            self.sort_ascending = True
        
        # Update file tree
        self.update_file_tree()
    
    def on_file_select(self, event):
        """Handles file selection in the treeview."""
        selection = self.file_tree.selection()
        if not selection:
            return
        
        # Get the file path from item tags
        item_id = selection[0]
        item_tags = self.file_tree.item(item_id, "tags")
        if not item_tags:
            return
        
        file_path = item_tags[0]
        
        # Find the file info
        for file in self.filtered_files:
            if file["path"] == file_path:
                self.current_file = file
                break
        
        # Update the UI
        self.update_file_info()
        self.update_current_tags()
        self.update_suggested_tags()
        self.preview_file()
    
    def update_file_info(self):
        """Updates the file info display."""
        if not self.current_file:
            self.file_info_var.set("No file selected")
            return
        
        file = self.current_file
        file_type = file["type"].capitalize()
        size = file["human_size"]
        
        if file["type"] in ["video", "audio"]:
            length = format_length(file["length"])
            self.file_info_var.set(f"{file['name']} - {file_type} - {size} - {length}")
        else:
            self.file_info_var.set(f"{file['name']} - {file_type} - {size}")
    
    def update_current_tags(self):
        """Updates the display of the current file's tags."""
        # Clear the current tags
        for widget in self.current_tags_frame.winfo_children():
            widget.destroy()
        
        if not self.current_file:
            return
        
        # Add tags
        file_tags = self.current_file.get("tags", [])
        
        if not file_tags:
            tk.Label(self.current_tags_frame, text="No tags").pack(side="left", padx=5)
            return
        
        tk.Label(self.current_tags_frame, text="Current Tags:").pack(side="left", padx=5)
        
        for tag in file_tags:
            tag_frame = tk.Frame(self.current_tags_frame, bd=1, relief="raised", padx=2, pady=2)
            tag_frame.pack(side="left", padx=2, pady=2)
            
            tk.Label(tag_frame, text=tag).pack(side="left")
            
            remove_btn = tk.Button(
                tag_frame, text="✕", bd=0, padx=2, pady=0,
                command=lambda t=tag: self.remove_tag(t)
            )
            remove_btn.pack(side="left")
    
    def update_suggested_tags(self):
        """Updates the suggested tags based on the current file."""
        # Clear the suggested tags
        for widget in self.suggested_tags_frame.winfo_children():
            widget.destroy()
    
        if not self.current_file:
            return
    
        filename = self.current_file["name"]
        full_path = self.current_file["path"]
        directory = os.path.dirname(full_path)
    
        # Generate tags from filename
        suggested_name = generate_suggested_tags(filename)
    
        # Add directory tags (depending on toggle)
        if directory:
            if self.full_path_tags_var.get():
                parts = os.path.normpath(directory).split(os.sep)
                for part in parts:
                    if part and part not in ["/", "\\", ""]:
                        suggested_name.append(part.lower())
            else:
                last_folder = os.path.basename(directory)
                suggested_name.append(last_folder.lower())

        suggested = list(set(suggested_name))

        # Remove tags that are already applied
        current_tags = self.current_file.get("tags", [])
        suggested = [tag for tag in suggested if tag not in current_tags]
    
        if not suggested:
            tk.Label(self.suggested_tags_frame, text="No suggestions").pack(side="left", padx=5)
            return
    
        for tag in suggested:
            tag_button = tk.Button(
                self.suggested_tags_frame, text=tag, padx=5, pady=2,
                command=lambda t=tag: self.quick_add_tag(t)
            )
            tag_button.pack(side="left", padx=2, pady=2)
    
    def update_popular_tags(self):
        """Updates the display of popular tags."""
        # Clear the popular tags
        for widget in self.popular_tags_frame.winfo_children():
            widget.destroy()
        
        # Get all tags
        all_tags = get_all_tags()
        
        if not all_tags:
            tk.Label(self.popular_tags_frame, text="No tags in system").pack(side="left", padx=5)
            return
        
        # Display top 10 tags
        for tag in all_tags[:10]:
            tag_button = tk.Button(
                self.popular_tags_frame, text=tag, padx=5, pady=2,
                command=lambda t=tag: self.quick_add_tag(t)
            )
            tag_button.pack(side="left", padx=2, pady=2)
    
    def update_tag_filter_combo(self):
        """Updates the tag filter combobox with all available tags."""
        all_tags = get_all_tags()
        self.tag_filter_combo["values"] = all_tags
    
    def add_tag_filter(self):
        """Adds a tag to the search filters."""
        tag = self.tag_filter_var.get()
        if tag and tag not in self.search_tags:
            self.search_tags.append(tag)
            self.tag_filter_var.set("")
            self.update_active_filters_display()
            self.apply_filters()
    
    def update_active_filters_display(self):
        """Updates the display of active tag filters."""
        # Clear the active filters
        for widget in self.active_filters_frame.winfo_children():
            widget.destroy()
        
        if not self.search_tags:
            return
        
        tk.Label(self.active_filters_frame, text="Active Tag Filters:").pack(side="left", padx=5)
        
        for tag in self.search_tags:
            tag_frame = tk.Frame(self.active_filters_frame, bd=1, relief="raised", padx=2, pady=2)
            tag_frame.pack(side="left", padx=2, pady=2)
            
            tk.Label(tag_frame, text=tag).pack(side="left")
            
            remove_btn = tk.Button(
                tag_frame, text="✕", bd=0, padx=2, pady=0,
                command=lambda t=tag: self.remove_tag_filter(t)
            )
            remove_btn.pack(side="left")
    
    def remove_tag_filter(self, tag):
        """Removes a tag from the search filters."""
        if tag in self.search_tags:
            self.search_tags.remove(tag)
            self.update_active_filters_display()
            self.apply_filters()
    
    def clear_filters(self):
        """Clears all filters."""
        self.search_tags = []
        self.filter_var.set("")
        self.update_active_filters_display()
        self.apply_filters()
    
    def add_tag(self):
        """Adds a tag to the current file."""
        if not self.current_file:
            messagebox.showinfo("Info", "Please select a file first")
            return
        
        tag = self.tag_entry_var.get().strip()
        if not tag:
            return
        
        if add_tag_to_file(self.current_file["path"], tag):
            # Update the file's tags
            self.current_file["tags"].append(tag)
            
            # Update UI
            self.update_current_tags()
            self.update_suggested_tags()
            self.update_file_tree()
            self.update_popular_tags()
            self.update_tag_filter_combo()
            self.update_active_filters_display()
            
            # Clear the tag entry
            self.tag_entry_var.set("")
    
    def quick_add_tag(self, tag):
        """Quickly adds a tag from suggestions or popular tags to selected files."""
        selected_items = self.file_tree.selection()
        if not selected_items:
            messagebox.showinfo("Info", "Please select one or more files.")
            return

        for item in selected_items:
            file_path = self.file_tree.item(item, 'tags')[0]
            for file in self.files:
                if file["path"] == file_path:
                    if add_tag_to_file(file["path"], tag):
                        if tag not in file["tags"]: # Prevent duplicates
                            file["tags"].append(tag)
        
        self.update_file_tree()
        self.update_current_tags() # Update UI to reflect changes
        self.update_suggested_tags()
    
    def remove_tag(self, tag):
        """Removes a tag from the selected files."""
        selected_items = self.file_tree.selection()
        if not selected_items:
            messagebox.showinfo("Info", "Please select one or more files.")
            return

        for item in selected_items:
            file_path = self.file_tree.item(item, 'tags')[0]
            for file in self.files:
                if file["path"] == file_path:
                    if remove_tag_from_file(file["path"], tag):
                        file["tags"] = [t for t in file["tags"] if t != tag]
        
        self.update_file_tree()
        self.update_current_tags()
        self.update_suggested_tags()
        self.update_popular_tags()
        self.update_tag_filter_combo()
    
    def preview_file(self):
        """Previews the selected file."""
        if not self.current_file:
            return
        
        # Clear the preview canvas
        self.preview_canvas.delete("all")
        
        # Stop any playing audio
        self.stop_media_playback()
        
        # Hide media controls
        self.play_button.pack_forget()
        
        file_path = self.current_file["path"]
        file_type = self.current_file["type"]
        
        try:
            if file_type == "image":
                self.preview_image(file_path)
            elif file_type == "audio":
                self.preview_audio(file_path)
            elif file_type == "video":
                self.preview_video(file_path)
            elif file_type == "document":
                self.preview_document(file_path)
            else:
                # Generic preview for other file types
                self.preview_canvas.create_text(
                    150, 150, text=f"No preview available for {self.current_file['name']}", 
                    fill="gray", font=("Arial", 12), width=280
                )
        except Exception as e:
            self.preview_canvas.create_text(
                150, 150, text=f"Error previewing file:\n{str(e)}", 
                fill="red", font=("Arial", 12), width=280
            )
    
    def preview_image(self, file_path):
        """Displays an image preview."""
        try:
            # Open the image
            img = Image.open(file_path)
            
            # Get canvas dimensions
            canvas_width = self.preview_canvas.winfo_width()
            canvas_height = self.preview_canvas.winfo_height()
            
            # Resize image to fit canvas while maintaining aspect ratio
            img_width, img_height = img.size
            ratio = min(canvas_width/img_width, canvas_height/img_height)
            new_width = int(img_width * ratio)
            new_height = int(img_height * ratio)
            
            img = img.resize((new_width, new_height), Image.LANCZOS)
            
            # Convert to PhotoImage
            photo = ImageTk.PhotoImage(img)
            
            # Display image
            self.preview_canvas.create_image(
                canvas_width // 2, canvas_height // 2, 
                image=photo, anchor="center"
            )
            
            # Keep a reference to prevent garbage collection
            self.preview_canvas.image = photo
            
        except Exception as e:
            # Display error message
            self.preview_canvas.create_text(
                150, 150, text=f"Error loading image:\n{str(e)}", 
                fill="red", font=("Arial", 12), width=280
            )
    
    def preview_audio(self, file_path):
        """Provides an audio preview interface."""
        # Display audio icon or waveform placeholder
        self.preview_canvas.create_text(
            150, 100, text="🎵 Audio File 🎵", 
            fill="blue", font=("Arial", 20)
        )
        
        file_name = os.path.basename(file_path)
        self.preview_canvas.create_text(
            150, 150, text=file_name, 
            fill="black", font=("Arial", 12)
        )
        
        # Show media controls
        self.current_audio = file_path
        self.play_button.config(text="▶ Play")
        self.play_button.pack(side="left", padx=5)
    
    def preview_video(self, file_path):
        """Provides a video preview (thumbnail)."""
        # First, try to get a thumbnail using OpenCV (if available) - this is faster
        try:
            import cv2
            cap = cv2.VideoCapture(file_path)
            ret, frame = cap.read()
            if ret:
                # Convert from BGR to RGB
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                img = Image.fromarray(frame_rgb)
                self.preview_image_from_pil(img)  # Helper function to display PIL Image
                cap.release()
                self.show_video_controls()
                return  # Success, exit the function
            else:
                cap.release()  # Release capture object if reading fails
                print("OpenCV failed to read video frame, falling back to ffmpeg")
        except ImportError:
            print("OpenCV not available, trying ffmpeg")
        except Exception as e:
            print(f"OpenCV error: {e}, falling back to ffmpeg")

        # --- Fallback to ffmpeg if OpenCV fails or isn't available ---
        try:
            # Create temporary file for thumbnail
            with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as temp_file:
                thumbnail_path = temp_file.name

            # Extract thumbnail using ffmpeg
            result = subprocess.run([
                "ffmpeg", "-i", file_path,
                "-ss", "00:00:01.000", "-vframes", "1",
                thumbnail_path
            ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

            if result.returncode == 0:
                self.preview_image(thumbnail_path)
                self.show_video_controls()
            else:
                print(f"ffmpeg error: {result.stderr.decode()}")
                self.show_generic_video_preview()  # Show a placeholder

            # Clean up (with better error handling)
            try:
                os.remove(thumbnail_path)
            except OSError as e:
                print(f"Error deleting thumbnail: {e}")

        except FileNotFoundError:
            print("ffmpeg not found. Please ensure it is installed and in your PATH.")
            self.show_generic_video_preview()
        except Exception as e:
            print(f"Error generating video thumbnail: {e}")
            self.show_generic_video_preview()

    def preview_image_from_pil(self, img):
        """Helper to display a PIL Image in the preview."""
        try:
            # Get canvas dimensions
            canvas_width = self.preview_canvas.winfo_width()
            canvas_height = self.preview_canvas.winfo_height()

            # Resize image to fit canvas while maintaining aspect ratio
            img_width, img_height = img.size
            ratio = min(canvas_width / img_width, canvas_height / img_height)
            new_width = int(img_width * ratio)
            new_height = int(img_height * ratio)

            img = img.resize((new_width, new_height), Image.LANCZOS)

            # Convert to PhotoImage
            photo = ImageTk.PhotoImage(img)

            # Display image
            self.preview_canvas.create_image(
                canvas_width // 2, canvas_height // 2,
                image=photo, anchor="center"
            )

            # Keep a reference to prevent garbage collection
            self.preview_canvas.image = photo

        except Exception as e:
            # Display error message
            self.preview_canvas.create_text(
                150, 150, text=f"Error loading image:\n{str(e)}",
                fill="red", font=("Arial", 12), width=280
            )

    def show_video_controls(self):
        """Helper function to show video controls."""
        self.play_button.config(text="▶ Open", bg="red")
        self.play_button.pack(side="left", padx=5)

    def show_generic_video_preview(self):
        """Helper function to display a placeholder for videos."""

        self.preview_canvas.create_text(
            150, 100, text="🎬 Video File 🎬",
            fill="purple", font=("Arial", 20)
        )

        file_name = os.path.basename(self.current_file["path"])
        self.preview_canvas.create_text(
            150, 150, text=file_name,
            fill="black", font=("Arial", 12)
        )
    
    def preview_document(self, file_path):
        """Provides a document preview."""
        file_ext = os.path.splitext(file_path)[1].lower()
        
        if file_ext == ".pdf":
            try:
                import fitz  # PyMuPDF
                
                # Open the PDF
                doc = fitz.open(file_path)
                
                if doc.page_count > 0:
                    # Get the first page
                    page = doc[0]
                    
                    # Render to an image
                    pix = page.get_pixmap(matrix=fitz.Matrix(0.5, 0.5))
                    
                    # Convert to PIL Image
                    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                    
                    # Get canvas dimensions
                    canvas_width = self.preview_canvas.winfo_width()
                    canvas_height = self.preview_canvas.winfo_height()
                    
                    # Resize to fit canvas
                    img_width, img_height = img.size
                    ratio = min(canvas_width/img_width, canvas_height/img_height)
                    new_width = int(img_width * ratio)
                    new_height = int(img_height * ratio)
                    
                    img = img.resize((new_width, new_height), Image.LANCZOS)
                    
                    # Convert to PhotoImage
                    photo = ImageTk.PhotoImage(img)
                    
                    # Display image
                    self.preview_canvas.create_image(
                        canvas_width // 2, canvas_height // 2, 
                        image=photo, anchor="center"
                    )
                    
                    # Keep a reference
                    self.preview_canvas.image = photo
                    
                    # Add page info
                    self.preview_canvas.create_text(
                        canvas_width // 2, 20, 
                        text=f"Page 1 of {doc.page_count}", 
                        fill="black", font=("Arial", 10)
                    )
                    
                    # Close the document
                    doc.close()
                    return
            except ImportError:
                pass  # PyMuPDF not available
            except Exception as e:
                print(f"PDF preview error: {e}")
        
        elif file_ext in [".txt", ".md", ".py", ".java", ".html", ".css", ".js"]:
            try:
                # Read the first few lines
                with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                    lines = [line.strip() for line in f.readlines()[:20]]
                
                # Join lines with newlines
                content = "\n".join(lines)
                
                # Display the text
                self.preview_canvas.create_text(
                    10, 10, text=content, 
                    fill="black", font=("Courier", 10), 
                    anchor="nw", width=self.preview_canvas.winfo_width() - 20
                )
                return
            except Exception as e:
                print(f"Text preview error: {e}")
        
        # Fallback for unsupported document types or if preview fails
        file_name = os.path.basename(file_path)
        self.preview_canvas.create_text(
            150, 100, text="📄 Document 📄", 
            fill="green", font=("Arial", 20)
        )
        self.preview_canvas.create_text(
            150, 150, text=file_name, 
            fill="black", font=("Arial", 12)
        )
    
    def toggle_media_playback(self):
        """Toggles audio playback."""
        if not self.current_file:
            return
        
        file_type = self.current_file["type"]
        file_path = self.current_file["path"]
        
        if file_type == "audio":
            if self.audio_playing:
                pygame.mixer.music.stop()
                self.audio_playing = False
                self.play_button.config(text="▶ Play")
            else:
                try:
                    pygame.mixer.music.load(file_path)
                    pygame.mixer.music.play()
                    self.audio_playing = True
                    self.play_button.config(text="⏹ Stop")
                except Exception as e:
                    messagebox.showerror("Error", f"Could not play audio: {str(e)}")
        elif file_type == "video":
            # Open video in default player
            self.open_file(None)
    
    def stop_media_playback(self):
        """Stops any playing media."""
        if self.audio_playing:
            pygame.mixer.music.stop()
            self.audio_playing = False
    
    def open_file(self, event):
        """Opens the selected file with the default application."""
        if not self.current_file:
            return
        
        file_path = self.current_file["path"]
        
        # Use the appropriate method based on the OS
        if os.name == 'nt':  # Windows
            os.startfile(file_path)
        elif os.name == 'posix':  # macOS and Linux
            if os.uname().sysname == 'Darwin':  # macOS
                subprocess.call(('open', file_path))
            else:  # Linux
                subprocess.call(('xdg-open', file_path))
                
    def open_containing_folder(self):
        """Opens the containing folder of the currently selected file."""
        if not self.current_file:
            messagebox.showinfo("Info", "Please select a file first")
            return

        folder_path = os.path.dirname(self.current_file["path"])

        try:
            if os.name == 'nt':  # Windows
                os.startfile(folder_path)  # type: ignore #startfile is valid for windows
            elif os.name == 'posix':  # macOS and Linux
                if os.uname().sysname == 'Darwin':  # macOS
                    subprocess.run(['open', folder_path])
                else:  # Linux
                    subprocess.run(['xdg-open', folder_path])
        except Exception as e:
            messagebox.showerror("Error", f"Could not open folder: {e}")
    
    def load_global_files(self):
        """Loads file information from the global tags.json file."""
        global_files = []
        if os.path.exists(TAG_FILE):
            with open(TAG_FILE, "r") as f:
                try:
                    tags_data = json.load(f)
                    for file_path, tags in tags_data.items():
                        # Extract information similar to list_files
                        file_name = os.path.basename(file_path)
                        name, ext = os.path.splitext(file_name)
                        size = (
                            os.path.getsize(file_path)
                            if os.path.exists(file_path)
                            else 0
                        )
                        file_type = get_file_type(file_name)
                        length = get_file_length(file_path)
                        modified = (
                            os.path.getmtime(file_path)
                            if os.path.exists(file_path)
                            else 0
                        )
                        
                        global_files.append(
                            {
                                "name": file_name,
                                "basename": name,
                                "path": file_path,
                                "ext": ext.lower(),
                                "size": size,
                                "human_size": naturalsize(size),
                                "type": file_type,
                                "length": length,
                                "modified": modified,
                                "tags": tags,
                                "directory": os.path.dirname(
                                    file_path
                                ),  # Add directory
                            }
                        )
                except json.JSONDecodeError:
                    messagebox.showerror(
                        "Error",
                        "Error reading tags.json.  File may be corrupted.",
                    )
        return global_files

if __name__ == "__main__":
    root = tk.Tk()
    app = TagzApp(root)
    root.mainloop()