import sys
import os
import re
import time
import requests
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QProgressBar, QComboBox, QFileDialog,
    QMessageBox, QGroupBox
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QSettings
from PyQt5.QtGui import QFont

class DownloadThread(QThread):
    progress_updated = pyqtSignal(float, float, float)
    finished = pyqtSignal(bool, str)
    log_message = pyqtSignal(str)
    
    def __init__(self, repo_id, filename, local_dir, endpoint):
        super().__init__()
        self.repo_id = repo_id
        self.filename = filename
        self.local_dir = local_dir
        self.endpoint = endpoint
        self._is_paused = False
        self._is_stopped = False
        self.downloaded_bytes = 0
        self.total_bytes = 0
    
    def pause(self):
        self._is_paused = True
    
    def resume(self):
        self._is_paused = False
    
    def stop(self):
        self._is_stopped = True
    
    def run(self):
        try:
            if not os.path.exists(self.local_dir):
                os.makedirs(self.local_dir, exist_ok=True)
            self._download()
        except Exception as e:
            self.finished.emit(False, f"下载失败: {str(e)}")
    
    def _download(self):
        
        file_url = f"https://huggingface.co/{self.repo_id}/resolve/main/{self.filename}"
        if "hf-mirror.com" in self.endpoint:
            file_url = f"https://hf-mirror.com/{self.repo_id}/resolve/main/{self.filename}"
        
        self.log_message.emit(f"下载地址: {file_url}")
        
        local_path = os.path.join(self.local_dir, os.path.basename(self.filename))
        temp_path = local_path + ".tmp"
        
        headers = {}
        if os.path.exists(temp_path):
            self.downloaded_bytes = os.path.getsize(temp_path)
            headers["Range"] = f"bytes={self.downloaded_bytes}-"
            self.log_message.emit(f"断点续传，已下载: {self._format_size(self.downloaded_bytes)}")
        
        response = requests.get(file_url, headers=headers, stream=True, timeout=30)
        
        if response.status_code == 416:
            self.log_message.emit("文件已完整下载")
            if os.path.exists(temp_path):
                os.rename(temp_path, local_path)
            self.progress_updated.emit(100, 0, 0)
            self.finished.emit(True, f"下载成功！文件已保存到: {local_path}")
            return
        
        if response.status_code not in [200, 206]:
            self.finished.emit(False, f"下载失败: HTTP {response.status_code}")
            return
        
        self.total_bytes = int(response.headers.get('content-length', 0))
        if response.status_code == 206:
            content_range = response.headers.get('content-range', '')
            if '/' in content_range:
                self.total_bytes = int(content_range.split('/')[-1])
        elif self.total_bytes == 0:
            self.total_bytes = self.downloaded_bytes + int(response.headers.get('content-length', 0))
        
        self.log_message.emit(f"文件大小: {self._format_size(self.total_bytes)}")
        
        start_time = time.time()
        last_time = start_time
        last_bytes = self.downloaded_bytes
        
        mode = 'ab' if self.downloaded_bytes > 0 else 'wb'
        with open(temp_path, mode) as f:
            for chunk in response.iter_content(chunk_size=8192):
                if self._is_stopped:
                    self.log_message.emit("下载已取消")
                    self.finished.emit(False, "下载已取消")
                    return
                
                while self._is_paused:
                    time.sleep(0.1)
                    if self._is_stopped:
                        self.log_message.emit("下载已取消")
                        self.finished.emit(False, "下载已取消")
                        return
                
                if chunk:
                    f.write(chunk)
                    self.downloaded_bytes += len(chunk)
                    
                    current_time = time.time()
                    elapsed = current_time - last_time
                    
                    if elapsed >= 0.5:
                        if self.total_bytes > 0:
                            progress = (self.downloaded_bytes / self.total_bytes) * 100
                        else:
                            progress = 0
                        
                        speed = (self.downloaded_bytes - last_bytes) / elapsed / (1024 * 1024)
                        
                        if speed > 0:
                            remaining_bytes = self.total_bytes - self.downloaded_bytes
                            eta = remaining_bytes / (speed * 1024 * 1024)
                        else:
                            eta = float('inf')
                        
                        self.progress_updated.emit(progress, speed, eta)
                        
                        last_time = current_time
                        last_bytes = self.downloaded_bytes
        
        if os.path.exists(local_path):
            os.remove(local_path)
        os.rename(temp_path, local_path)
        
        self.progress_updated.emit(100, 0, 0)
        self.finished.emit(True, f"下载成功！文件已保存到: {local_path}")
    
    def _format_size(self, bytes_size):
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if bytes_size < 1024.0:
                return f"{bytes_size:.2f} {unit}"
            bytes_size /= 1024.0
        return f"{bytes_size:.2f} PB"


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("HuggingFace 模型下载器")
        self.setGeometry(100, 100, 700, 550)
        self.setMinimumSize(600, 450)
        
        self.settings = QSettings("HuggingFace", "ModelDownloader")
        
        self._apply_style()
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QVBoxLayout()
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(20, 20, 20, 20)
        central_widget.setLayout(main_layout)
        
        title_label = QLabel("🤗 HuggingFace 模型下载器")
        title_label.setFont(QFont("Microsoft YaHei", 18, QFont.Bold))
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("color: #2c3e50; margin-bottom: 10px;")
        main_layout.addWidget(title_label)
        
        url_group = QGroupBox("下载设置")
        url_group.setStyleSheet(self._get_group_style())
        url_layout = QVBoxLayout()
        url_layout.setSpacing(10)
        url_group.setLayout(url_layout)
        
        url_label = QLabel("模型文件URL")
        url_label.setFont(QFont("Microsoft YaHei", 10))
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("https://huggingface.co/owner/repo/blob/main/filename.safetensors")
        self.url_input.setStyleSheet(self._get_input_style())
        self.url_input.setMinimumHeight(36)
        url_layout.addWidget(url_label)
        url_layout.addWidget(self.url_input)
        
        source_layout = QHBoxLayout()
        source_label = QLabel("下载源")
        source_label.setFont(QFont("Microsoft YaHei", 10))
        source_label.setFixedWidth(80)
        self.source_combo = QComboBox()
        self.source_combo.addItem("HF Mirror (国内推荐)", "https://hf-mirror.com/")
        self.source_combo.addItem("HuggingFace 官方", "https://huggingface.co/")
        self.source_combo.setStyleSheet(self._get_combo_style())
        self.source_combo.setMinimumHeight(36)
        source_layout.addWidget(source_label)
        source_layout.addWidget(self.source_combo)
        url_layout.addLayout(source_layout)
        
        dir_layout = QHBoxLayout()
        dir_label = QLabel("保存目录")
        dir_label.setFont(QFont("Microsoft YaHei", 10))
        dir_label.setFixedWidth(80)
        self.dir_input = QLineEdit()
        self.dir_input.setText("./models")
        self.dir_input.setStyleSheet(self._get_input_style())
        self.dir_input.setMinimumHeight(36)
        browse_btn = QPushButton("📁 浏览")
        browse_btn.setStyleSheet(self._get_button_style("#3498db"))
        browse_btn.setMinimumHeight(36)
        browse_btn.clicked.connect(self.browse_directory)
        dir_layout.addWidget(dir_label)
        dir_layout.addWidget(self.dir_input)
        dir_layout.addWidget(browse_btn)
        url_layout.addLayout(dir_layout)
        
        main_layout.addWidget(url_group)
        
        progress_group = QGroupBox("下载进度")
        progress_group.setStyleSheet(self._get_group_style())
        progress_layout = QVBoxLayout()
        progress_layout.setSpacing(8)
        progress_group.setLayout(progress_layout)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.progress_bar.setMinimumHeight(25)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 2px solid #bdc3c7;
                border-radius: 8px;
                text-align: center;
                background-color: #ecf0f1;
                font-weight: bold;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #3498db, stop:1 #2ecc71);
                border-radius: 6px;
            }
        """)
        progress_layout.addWidget(self.progress_bar)
        
        info_layout = QHBoxLayout()
        self.progress_label = QLabel("0.0%")
        self.progress_label.setFont(QFont("Microsoft YaHei", 11, QFont.Bold))
        self.progress_label.setStyleSheet("color: #2c3e50;")
        self.speed_label = QLabel("0.00 MB/s")
        self.speed_label.setFont(QFont("Microsoft YaHei", 10))
        self.speed_label.setStyleSheet("color: #7f8c8d;")
        self.eta_label = QLabel("剩余时间: --")
        self.eta_label.setFont(QFont("Microsoft YaHei", 10))
        self.eta_label.setStyleSheet("color: #7f8c8d;")
        info_layout.addWidget(self.progress_label)
        info_layout.addStretch()
        info_layout.addWidget(self.speed_label)
        info_layout.addStretch()
        info_layout.addWidget(self.eta_label)
        progress_layout.addLayout(info_layout)
        
        self.status_label = QLabel("就绪")
        self.status_label.setFont(QFont("Microsoft YaHei", 9))
        self.status_label.setStyleSheet("color: #95a5a6;")
        progress_layout.addWidget(self.status_label)
        
        main_layout.addWidget(progress_group)
        
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)
        
        self.download_btn = QPushButton("▶ 开始下载")
        self.download_btn.setStyleSheet(self._get_button_style("#27ae60", large=True))
        self.download_btn.setMinimumHeight(45)
        self.download_btn.clicked.connect(self.start_download)
        
        self.pause_btn = QPushButton("⏸ 暂停")
        self.pause_btn.setStyleSheet(self._get_button_style("#f39c12"))
        self.pause_btn.setMinimumHeight(45)
        self.pause_btn.clicked.connect(self.pause_download)
        self.pause_btn.setEnabled(False)
        
        self.stop_btn = QPushButton("⏹ 停止")
        self.stop_btn.setStyleSheet(self._get_button_style("#e74c3c"))
        self.stop_btn.setMinimumHeight(45)
        self.stop_btn.clicked.connect(self.stop_download)
        self.stop_btn.setEnabled(False)
        
        self.exit_btn = QPushButton("✕ 退出")
        self.exit_btn.setStyleSheet(self._get_button_style("#95a5a6"))
        self.exit_btn.setMinimumHeight(45)
        self.exit_btn.clicked.connect(self.close)
        
        btn_layout.addWidget(self.download_btn)
        btn_layout.addWidget(self.pause_btn)
        btn_layout.addWidget(self.stop_btn)
        btn_layout.addWidget(self.exit_btn)
        
        main_layout.addLayout(btn_layout)
        main_layout.addStretch()
        
        self.download_thread = None
        self.is_paused = False
        
        self._load_settings()
    
    def _apply_style(self):
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f5f6fa;
            }
            QWidget {
                font-family: "Microsoft YaHei", "Segoe UI", Arial;
            }
        """)
    
    def _get_group_style(self):
        return """
            QGroupBox {
                font-weight: bold;
                font-size: 11px;
                border: 2px solid #dcdde1;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 10px;
                background-color: white;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 15px;
                padding: 0 5px;
                color: #2c3e50;
            }
        """
    
    def _get_input_style(self):
        return """
            QLineEdit {
                border: 2px solid #dcdde1;
                border-radius: 6px;
                padding: 5px 10px;
                background-color: white;
                font-size: 10px;
            }
            QLineEdit:focus {
                border-color: #3498db;
            }
        """
    
    def _get_combo_style(self):
        return """
            QComboBox {
                border: 2px solid #dcdde1;
                border-radius: 6px;
                padding: 5px 10px;
                background-color: white;
                font-size: 10px;
            }
            QComboBox:focus {
                border-color: #3498db;
            }
            QComboBox::drop-down {
                border: none;
                width: 30px;
            }
            QComboBox::down-arrow {
                width: 12px;
                height: 12px;
            }
        """
    
    def _get_button_style(self, color, large=False):
        padding = "12px 20px" if large else "8px 15px"
        font_size = "12px" if large else "10px"
        return f"""
            QPushButton {{
                background-color: {color};
                color: white;
                border: none;
                border-radius: 6px;
                padding: {padding};
                font-size: {font_size};
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {self._darken_color(color)};
            }}
            QPushButton:disabled {{
                background-color: #bdc3c7;
            }}
        """
    
    def _darken_color(self, hex_color):
        color_map = {
            "#27ae60": "#1e8449",
            "#3498db": "#2980b9",
            "#e74c3c": "#c0392b",
            "#f39c12": "#d68910",
            "#95a5a6": "#7f8c8d"
        }
        return color_map.get(hex_color, hex_color)
    
    def _load_settings(self):
        source_index = self.settings.value("source_index", 0, type=int)
        self.source_combo.setCurrentIndex(source_index)
        
        save_dir = self.settings.value("save_directory", "./models")
        self.dir_input.setText(save_dir)
    
    def _save_settings(self):
        self.settings.setValue("source_index", self.source_combo.currentIndex())
        self.settings.setValue("save_directory", self.dir_input.text())
    
    def browse_directory(self):
        directory = QFileDialog.getExistingDirectory(self, "选择下载目录")
        if directory:
            self.dir_input.setText(directory)
    
    def parse_huggingface_url(self, url):
        regex = r"https://huggingface\.co/([^/]+/[^/]+)/blob/[^/]+/(.+)"
        match = re.match(regex, url)
        if match:
            return {
                "repo_id": match.group(1),
                "filename": match.group(2)
            }
        regex_datasets = r"https://huggingface\.co/datasets/([^/]+/[^/]+)/blob/[^/]+/(.+)"
        match = re.match(regex_datasets, url)
        if match:
            return {
                "repo_id": f"datasets/{match.group(1)}",
                "filename": match.group(2)
            }
        return None
    
    def start_download(self):
        url = self.url_input.text().strip()
        source = self.source_combo.currentData()
        local_dir = self.dir_input.text().strip()
        
        if not url:
            QMessageBox.warning(self, "提示", "请输入模型文件URL")
            return
        
        if not local_dir:
            QMessageBox.warning(self, "提示", "请设置保存目录")
            return
        
        self._save_settings()
        
        parsed = self.parse_huggingface_url(url)
        if not parsed:
            QMessageBox.warning(self, "提示", "无效的Hugging Face URL\n\n正确格式:\nhttps://huggingface.co/owner/repo/blob/main/filename")
            return
        
        self.download_btn.setEnabled(False)
        self.pause_btn.setEnabled(True)
        self.stop_btn.setEnabled(True)
        self.pause_btn.setText("⏸ 暂停")
        self.is_paused = False
        
        self.status_label.setText("正在下载...")
        self.status_label.setStyleSheet("color: #27ae60;")
        
        self.download_thread = DownloadThread(
            parsed["repo_id"],
            parsed["filename"],
            local_dir,
            source
        )
        self.download_thread.progress_updated.connect(self.update_progress)
        self.download_thread.finished.connect(self.download_finished)
        self.download_thread.log_message.connect(self.log_status)
        self.download_thread.start()
    
    def pause_download(self):
        if self.download_thread:
            if self.is_paused:
                self.download_thread.resume()
                self.pause_btn.setText("⏸ 暂停")
                self.status_label.setText("正在下载...")
                self.status_label.setStyleSheet("color: #27ae60;")
                self.is_paused = False
            else:
                self.download_thread.pause()
                self.pause_btn.setText("▶ 继续")
                self.status_label.setText("已暂停")
                self.status_label.setStyleSheet("color: #f39c12;")
                self.is_paused = True
    
    def stop_download(self):
        if self.download_thread:
            reply = QMessageBox.question(
                self, "确认", "确定要取消下载吗？",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                self.download_thread.stop()
    
    def update_progress(self, progress, speed, eta):
        self.progress_bar.setValue(int(progress))
        self.progress_label.setText(f"{progress:.1f}%")
        self.speed_label.setText(f"{speed:.2f} MB/s")
        
        if eta == float('inf') or eta < 0:
            eta_str = "计算中..."
        elif eta > 3600:
            hours = int(eta // 3600)
            minutes = int((eta % 3600) // 60)
            eta_str = f"{hours}时{minutes}分"
        elif eta > 60:
            minutes = int(eta // 60)
            seconds = int(eta % 60)
            eta_str = f"{minutes}分{seconds}秒"
        else:
            eta_str = f"{int(eta)}秒"
        
        self.eta_label.setText(f"剩余时间: {eta_str}")
    
    def log_status(self, message):
        if message.strip():
            self.status_label.setText(message[:50] + "..." if len(message) > 50 else message)
    
    def download_finished(self, success, message):
        self.download_btn.setEnabled(True)
        self.pause_btn.setEnabled(False)
        self.stop_btn.setEnabled(False)
        self.pause_btn.setText("⏸ 暂停")
        self.is_paused = False
        
        if success:
            self.status_label.setText("下载完成！")
            self.status_label.setStyleSheet("color: #27ae60;")
            self.progress_bar.setValue(100)
            QMessageBox.information(self, "成功", message)
        else:
            self.status_label.setText("下载失败")
            self.status_label.setStyleSheet("color: #e74c3c;")
            QMessageBox.critical(self, "错误", message)
        
        self.download_thread = None
    
    def closeEvent(self, event):
        self._save_settings()
        
        if self.download_thread and self.download_thread.isRunning():
            reply = QMessageBox.question(
                self, "确认退出",
                "下载正在进行中，确定要退出吗？",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                self.download_thread.stop()
                self.download_thread.wait(1000)
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())