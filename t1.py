import sys
import threading
import time
import os
from datetime import datetime
import webbrowser

import requests
from PySide6.QtWidgets import (QApplication, QMainWindow, QLabel, QListWidget,
                               QPushButton, QVBoxLayout, QWidget, QListWidgetItem,
                               QMessageBox, QSystemTrayIcon, QMenu, QStyle,
                               QHBoxLayout, QLineEdit, QFrame) # QFrame 추가
from PySide6.QtCore import Qt, QObject, Signal, QEvent
from PySide6.QtGui import QIcon, QPixmap, QFontDatabase # QFontDatabase 추가

from pydub import AudioSegment
from pydub.playback import play

# --- 밝고 깔끔한 테마 (이전과 동일) ---
# ELEGANT_THEME (더 세련된 밝은 테마)
ELEGANT_THEME = """
/* 기본 위젯 스타일 */
QWidget {
    font-family: 'Noto Sans KR', '맑은 고딕', 'Malgun Gothic', sans-serif; /* 폰트 변경 */
    color: #34495E; /* 기본 글자색 (짙은 청회색) */
    background-color: #F8F9FA; /* 부드러운 배경색 */
}

QMainWindow {
    background-color: #F8F9FA;
    border-radius: 10px; /* 창 자체도 둥글게 */
}

/* 컨테이너 프레임 스타일 */
QFrame#mainContainer, QFrame#inputFrame, QFrame#listFrame, QFrame#buttonFrame {
    background-color: #FFFFFF; /* 내부 프레임 배경은 흰색 */
    border: 1px solid #E0E0E0; /* 옅은 테두리 */
    border-radius: 8px; /* 둥근 모서리 */
    padding: 10px;
    margin: 5px;
    box-shadow: 2px 2px 5px rgba(0, 0, 0, 0.05); /* 은은한 그림자 */
}

QLabel {
    font-size: 14px;
    color: #495057;
    padding: 5px;
    background-color: transparent;
    font-weight: 500; /* 조금 더 굵게 */
}

/* 상태 라벨 (작은 글씨) */
QLabel#statusLabel {
    font-size: 12px;
    color: #6C7A89;
    font-style: italic;
    padding: 3px;
    background-color: transparent;
    margin-top: 5px;
}

/* QLineEdit (입력 필드) 스타일 */
QLineEdit {
    background-color: #F8F9FA;
    border: 1px solid #CED4DA;
    border-radius: 5px;
    padding: 8px 10px;
    font-size: 14px;
    color: #34495E;
}
QLineEdit:focus {
    border: 1px solid #449BFF; /* 포커스 시 파란색 테두리 */
    background-color: #FFFFFF;
}

/* QListWidget 스타일 */
QListWidget {
    background-color: #FFFFFF;
    border: 1px solid #E0E0E0;
    border-radius: 8px;
    font-size: 13px;
    padding: 5px;
    min-height: 150px; /* 최소 높이 설정 */
}

QListWidget::item {
    padding: 10px;
    border-bottom: 1px solid #F0F0F0; /* 얇은 구분선 */
    border-radius: 5px;
}
QListWidget::item:last {
    border-bottom: none; /* 마지막 아이템에는 구분선 없음 */
}

QListWidget::item:hover {
    background-color: #EBF5FB; /* 부드러운 하늘색 호버 효과 */
}

QListWidget::item:selected {
    background-color: #48ABFF;
    color: #FFFFFF;
}

/* QPushButton 스타일 (일반) */
QPushButton {
    background-color: #48ABFF; /* 메인 파란색 */
    color: #FFFFFF;
    font-size: 14px;
    font-weight: bold;
    border: none;
    border-radius: 6px;
    padding: 10px 15px;
    margin: 3px; /* 버튼 간 여백 */
    min-height: 30px;
}

QPushButton:hover {
    background-color: #0069D9;
}

QPushButton:pressed {
    background-color: #48ABFF;
    padding-top: 11px; /* 눌림 효과 */
    padding-bottom: 9px;
}

/* 알람 토글 버튼 */
QPushButton#toggleAlarmButton {
    background-color: #28A745; /* 녹색 */
}
QPushButton#toggleAlarmButton:hover {
    background-color: #218838;
}
QPushButton#toggleAlarmButton:pressed {
    background-color: #1E7E34;
}

/* 스크롤바 스타일 */
QScrollBar:vertical {
    border: none;
    background: #E9ECEF;
    width: 10px;
    margin: 0px 0px 0px 0px;
}

QScrollBar::handle:vertical {
    background: #CED4DA;
    min-height: 20px;
    border-radius: 5px;
}

QScrollBar::handle:vertical:hover {
    background: #ADB5BD;
}

/* QMessageBox 스타일 */
QMessageBox {
    background-color: #FFFFFF;
    border: 1px solid #DEE2E6;
    border-radius: 5px;
}
QMessageBox QLabel {
    color: #34495E;
    font-size: 13px;
}
QMessageBox QPushButton {
    background-color: #007BFF;
    color: #FFFFFF;
    border-radius: 5px;
    padding: 5px 10px;
}
QMessageBox QPushButton:hover {
    background-color: #0069D9;
}
"""

class AlarmSignalEmitter(QObject):
    notify = Signal(dict)
    # **[추가]** 자동 설정 완료 후 메시지를 표`시하기 위한 시그널
    auto_set_finished = Signal(str)
    rating_info_loaded = Signal(str)

# get_competition_data 함수는 이전과 동일
def get_competition_data():
    API_URL = "https://codeforces.com/api/contest.list?"
    try:
        response = requests.get(API_URL)
        response.raise_for_status()
        data = response.json()
        if data.get('status') == 'OK':
            competitions = data.get('result', [])
            contest_list = [
                {
                    'name': comp.get('name', '이름 없음'),
                    'time': datetime.fromtimestamp(comp.get('startTimeSeconds')).strftime("%Y-%m-%d %H:%M:%S"),
                    'url': f"https://codeforces.com/contest/{comp.get('id', '')}"
                }
                for comp in competitions if comp.get('type') != 'GYM' and comp.get('phase') == 'BEFORE'
            ]
            contest_list.reverse()
            return contest_list
        return None
    except requests.exceptions.RequestException:
        return None

from PySide6.QtWidgets import QHBoxLayout, QLineEdit
import webbrowser

class AlarmApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.competitions = []
        self.set_alarms = {}

        self.alarm_emitter = AlarmSignalEmitter()
        self.alarm_emitter.notify.connect(self.show_alarm_notification)
        self.alarm_emitter.auto_set_finished.connect(
            lambda msg: QMessageBox.information(self, "자동 설정 완료", msg)
        )
        self.alarm_emitter.rating_info_loaded.connect(
            lambda msg: QMessageBox.information(self, "레이팅 정보", msg)
        )
        
        # 아이콘 로드 (이전과 동일)
        self.alarm_icon = self.style().standardIcon(QStyle.StandardPixmap.SP_MessageBoxInformation)
        if os.path.exists(resource_path("clock.png")): self.clock_icon = QIcon(resource_path("clock.png"))
        else: self.clock_icon = self.style().standardIcon(QStyle.StandardPixmap.SP_DialogApplyButton)
        self.no_icon = QIcon()

        self.init_ui()
        self.load_competitions()

        self._center_window()
    
    def changeEvent(self, event):
        super(AlarmApp, self).changeEvent(event)
        if event.type() == QEvent.Type.WindowStateChange:
            if self.isMinimized():
                self.hide()
                event.ignore()

    def init_ui(self):
        self.setWindowTitle("Codeforces 대회 알람")
        self.setGeometry(300, 300, 600, 800) # 창 크기 약간 키움

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(10, 10, 10, 10) # 전체 여백 추가

        # --- ▼ 로고 이미지 추가 (이전과 동일) ▼ ---
        if os.path.exists(resource_path("logo.png")):
            pixmap = QPixmap(resource_path("logo.png"))
            logo_label = QLabel(self)
            logo_label.setPixmap(pixmap)
            logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            logo_label.setMaximumHeight(200)
            main_layout.addWidget(logo_label)
        # --- ▲ 로고 이미지 추가 ▲ ---

        # 핸들 입력 및 버튼들을 담을 QFrame
        input_frame = QFrame()
        input_frame.setObjectName("inputFrame") # QSS 적용을 위한 objectName 설정
        input_layout = QVBoxLayout(input_frame)
        input_layout.setContentsMargins(15, 15, 15, 15) # 내부 여백

        handle_input_layout = QHBoxLayout()
        self.handle_input = QLineEdit(self)
        self.handle_input.setPlaceholderText("Codeforces 핸들을 입력하세요")
        handle_input_layout.addWidget(self.handle_input)
        input_layout.addLayout(handle_input_layout)
        
        button_layout = QHBoxLayout()
        self.show_rating_button = QPushButton("내 레이팅 확인")
        self.show_rating_button.clicked.connect(self.show_my_rating)
        button_layout.addWidget(self.show_rating_button)

        self.auto_set_button = QPushButton("Rated 대회 알람 모두 설정")
        self.auto_set_button.clicked.connect(self.run_auto_set_alarms)
        button_layout.addWidget(self.auto_set_button)
        input_layout.addLayout(button_layout)
        
        main_layout.addWidget(input_frame) # 메인 레이아웃에 프레임 추가

        # 상태 라벨
        self.status_label = QLabel("대회 정보를 불러오는 중...")
        self.status_label.setObjectName("statusLabel") # QSS 적용
        main_layout.addWidget(self.status_label)

        # 대회 목록을 담을 QFrame
        list_frame = QFrame()
        list_frame.setObjectName("listFrame") # QSS 적용
        list_layout = QVBoxLayout(list_frame)
        list_layout.setContentsMargins(15, 15, 15, 15)

        self.competition_list = QListWidget()
        self.competition_list.currentItemChanged.connect(self._update_button_state)
        self.competition_list.itemDoubleClicked.connect(self._open_contest_page)
        list_layout.addWidget(self.competition_list)
        
        main_layout.addWidget(list_frame) # 메인 레이아웃에 프레임 추가

        # 개별 알람 설정/취소 버튼
        toggle_button_frame = QFrame()
        toggle_button_frame.setObjectName("buttonFrame")
        toggle_button_layout = QVBoxLayout(toggle_button_frame)
        toggle_button_layout.setContentsMargins(15, 15, 15, 15)

        self.toggle_alarm_button = QPushButton("대회를 선택해주세요")
        self.toggle_alarm_button.setObjectName("toggleAlarmButton") # QSS 적용
        self.toggle_alarm_button.setEnabled(False)
        self.toggle_alarm_button.clicked.connect(self.toggle_selected_alarm)
        toggle_button_layout.addWidget(self.toggle_alarm_button)

        main_layout.addWidget(toggle_button_frame)

        # 시스템 트레이 (이전과 동일)
        self.tray_icon = QSystemTrayIcon(self)
        if os.path.exists(resource_path("app_icon.ico")):
            self.tray_icon.setIcon(QIcon(resource_path("app_icon.ico")))
        else:
            self.tray_icon.setIcon(self.alarm_icon)
        self.tray_icon.activated.connect(self.handle_tray_activation)
        tray_menu = QMenu()
        tray_menu.addAction("열기", self.showNormal)
        tray_menu.addAction("종료", QApplication.instance().quit)
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.show()

    def _update_button_state(self, current_item, previous_item):
        if not current_item:
            self.toggle_alarm_button.setText("대회를 선택해주세요")
            self.toggle_alarm_button.setIcon(self.no_icon) # 아이콘도 초기화
            self.toggle_alarm_button.setEnabled(False)
            return

        self.toggle_alarm_button.setEnabled(True)
        comp_name = current_item.text().split('\n')[0]

        if comp_name in self.set_alarms:
            self.toggle_alarm_button.setText("✔️ 선택한 대회 알람 취소")
            self.toggle_alarm_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DialogCancelButton)) # 취소 아이콘
        else:
            self.toggle_alarm_button.setText("⏰ 선택한 대회 알람 설정")
            self.toggle_alarm_button.setIcon(self.alarm_icon) # 설정 아이콘
    
        # **[추가]** 알람 자동 설정 프로세스를 시작하는 함수
    def run_auto_set_alarms(self):
        handle = self.handle_input.text()
        if not handle:
            QMessageBox.warning(self, "경고", "Codeforces 핸들을 입력해주세요.")
            return

        # UI가 멈추지 않도록 별도 스레드에서 실행
        thread = threading.Thread(target=self._auto_set_logic, args=(handle,))
        thread.daemon = True
        thread.start()

    # **[추가]** 알람 자동 설정의 실제 로직 (스레드에서 실행)
    def _auto_set_logic(self, handle):
        self.status_label.setText(f"'{handle}' 님의 레이팅을 조회하는 중...")
        rating = self._get_user_rating(handle)

        if rating is None:
            self.status_label.setText(f"'{handle}' 님을 찾을 수 없거나 API 오류가 발생했습니다.")
            return
        
        self.status_label.setText(f"'{handle}' 님 레이팅: {rating} | 알람을 자동 설정하는 중...")
        
        set_count = 0
        # 전체 대회 목록을 순회
        for i in range(len(self.competitions)):
            contest = self.competitions[i]
            comp_name = contest['name']
            
            # 1. rated 대회인지, 2. 알람이 아직 설정되지 않았는지 확인
            if self._is_eligible(rating, comp_name) and comp_name not in self.set_alarms:
                item = self.competition_list.item(i)
                self._set_alarm(contest, item)
                set_count += 1
        
        # 메인 스레드에 결과 메시지를 보내달라고 요청
        self.alarm_emitter.auto_set_finished.emit(
            f"'{handle}' 님({rating})을 위한 {set_count}개의 rated 대회 알람이 새로 설정되었습니다."
        )
        if set_count == 0:
            self.status_label.setText(f"'{handle}' 님({rating}) | 새로 설정할 알람이 없습니다.")
        else:
            self.status_label.setText(f"'{handle}' 님({rating}) | {set_count}개 알람 자동 설정 완료!")

    # **[추가]** 알람 '설정' 로직을 별도 함수로 분리
    def _set_alarm(self, competition, item):
        comp_name = competition['name']
        cancel_event = threading.Event()    
        alarm_thread = threading.Thread(
            target=self._run_alarm_logic, args=(competition, cancel_event)
        )
        alarm_thread.daemon = True
        alarm_thread.start()
        
        self.set_alarms[comp_name] = {
            'item': item, 'thread': alarm_thread, 'event': cancel_event
        }
        item.setIcon(self.clock_icon)

    # **[추가]** 알람 '취소' 로직을 별도 함수로 분리
    def _cancel_alarm(self, competition, item):
        comp_name = competition['name']
        if comp_name in self.set_alarms:
            self.set_alarms[comp_name]['event'].set()
            self.set_alarms[comp_name]['item'].setIcon(self.no_icon)
            del self.set_alarms[comp_name]

    # **[수정]** 알람 설정과 취소를 모두 처리하는 토글 함수
    def toggle_selected_alarm(self):
        selected_item = self.competition_list.currentItem()
        if not selected_item: return

        selected_index = self.competition_list.row(selected_item)
        selected_competition = self.competitions[selected_index]
        comp_name = selected_competition['name']
        
        if comp_name in self.set_alarms:
            self._cancel_alarm(selected_competition, selected_item)
        else:
            self._set_alarm(selected_competition, selected_item)

        self._update_button_state(selected_item, None)
    # **[수정]** cancel_event를 받아 대기하며, 취소 가능한 로직으로 변경
    def _run_alarm_logic(self, competition_info, cancel_event):
        try:
            alarm_time = datetime.strptime(competition_info['time'], "%Y-%m-%d %H:%M:%S")
            now = datetime.now()

            if now >= alarm_time: return

            wait_seconds = (alarm_time - now).total_seconds()
            
            # event.wait(t)는 t초 동안 기다리다가, 중간에 event.set()이 호출되면 True를 반환
            is_cancelled = cancel_event.wait(timeout=wait_seconds)
            
            if not is_cancelled:
                # wait()가 False를 반환하면 -> 시간 초과 -> 알람 울릴 시간!
                self.alarm_emitter.notify.emit(competition_info)
            # is_cancelled가 True이면 -> 중간에 취소됨 -> 아무것도 안 하고 스레드 종료

        except Exception as e:
            print(f"알람 스레드 오류: {e}")

    # --- 나머지 코드는 이전과 동일 ---

    def show_alarm_notification(self, competition_info):
        self.tray_icon.showMessage(
            "🔔 대회 시작!",
            f"'{competition_info['name']}'이(가) 지금 시작합니다!",
            QSystemTrayIcon.Information, 30000
        )
        comp_name = competition_info['name']
        if comp_name in self.set_alarms:
            item = self.set_alarms.pop(comp_name)['item']
            item.setIcon(self.no_icon)
            self._update_button_state(self.competition_list.currentItem(), None)

    def closeEvent(self, event):
        self.hide()
        event.ignore()

    def handle_tray_activation(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.showNormal()
            self.activateWindow()

    def load_competitions(self):
        self.status_label.setText("대회 정보를 불러오는 중...")
        thread = threading.Thread(target=self._fetch_and_display)
        thread.daemon = True
        thread.start()

    def _fetch_and_display(self):
        self.competitions = get_competition_data()
        if self.competitions:
            self.status_label.setText("알람을 설정할 대회를 선택하세요.")
            self.competition_list.clear()
            for comp in self.competitions:
                item_text = f"{comp.get('name', '이름 없음')}\n  └ {comp.get('time', '시간 없음')}"
                item = QListWidgetItem(item_text)
                self.competition_list.addItem(item)
        else:
            self.status_label.setText("대회 정보를 불러오지 못했습니다. 인터넷 연결을 확인하세요.")
    # 레이팅 조회 버튼을 눌렀을 때 실행될 메인 함수
    def load_rating_and_filter(self):
        handle = self.handle_input.text()
        if not handle:
            QMessageBox.warning(self, "경고", "Codeforces 핸들을 입력해주세요.")
            return

        # 별도 스레드에서 레이팅 조회 및 필터링 실행
        thread = threading.Thread(target=self._get_rating_and_apply_filter, args=(handle,))
        thread.daemon = True
        thread.start()

    # 실제 로직을 처리하는 내부 함수 (스레드에서 실행됨)
    def _get_rating_and_apply_filter(self, handle):
        self.status_label.setText(f"'{handle}' 님의 레이팅을 조회하는 중...")
        rating = self._get_user_rating(handle)

        if rating is None:
            self.status_label.setText(f"'{handle}' 님을 찾을 수 없거나 API 오류가 발생했습니다.")
            return

        self.status_label.setText(f"'{handle}' 님의 현재 레이팅: {rating} | 참가 가능한 대회를 강조 표시합니다.")
        
        # 리스트의 모든 항목을 순회하며 필터 적용
        for i in range(self.competition_list.count()):
            item = self.competition_list.item(i)
            contest = self.competitions[i]
            
            if self._is_eligible(rating, contest['name']):
                # 참가 가능하면 녹색 배경과 아이콘 추가
                item.setBackground(Qt.GlobalColor.green)
                item.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DialogApplyButton))
            else:
                # 참가 불가능하면 기본 상태로
                item.setBackground(Qt.GlobalColor.white)
                item.setIcon(QIcon()) # 아이콘 제거

    # API를 호출하여 사용자 레이팅을 가져오는 함수
    def _get_user_rating(self, handle):
        url = f"https://codeforces.com/api/user.rating?handle={handle}"
        try:
            response = requests.get(url)
            response.raise_for_status()
            data = response.json()
            if data['status'] == 'OK' and data['result']:
                # 가장 마지막 기록이 현재 레이팅
                return data['result'][-1]['newRating']
            return None
        except requests.exceptions.RequestException as e:
            print(f"레이팅 조회 API 오류: {e}")
            return None

    # 레이팅과 대회 이름으로 참가 가능 여부 판단
    def _is_eligible(self, rating, contest_name):
        name = contest_name.lower()
        # Div. 1
        if "div. 1" in name and "div. 2" not in name:
            return rating >= 1900
        # Div. 2
        if "div. 2" in name and "div. 1" not in name:
            return rating < 1900
        # Div. 3
        if "div. 3" in name:
            return rating < 1600
        # Div. 4
        if "div. 4" in name:
            return rating < 1400
        # Global, Div1+Div2 등은 모두 참가 가능
        if "global" in name or ("div. 1" in name and "div. 2" in name):
            return True
        return False # Educational 등 기타 대회

    # 아이템 더블클릭 시 대회 페이지를 여는 함수
    def _open_contest_page(self, item):
        row = self.competition_list.row(item)
        contest_url = self.competitions[row]['url']
        webbrowser.open(contest_url)
        QMessageBox.information(self, "페이지 열기", f"웹 브라우저에서 '{contest_url}' 페이지를 엽니다.\n대회 시작 전 'Register' 버튼을 눌러주세요!")
    # **[추가]** '내 레이팅 확인' 버튼 클릭 시 실행될 함수
    def show_my_rating(self):
        handle = self.handle_input.text()
        if not handle:
            QMessageBox.warning(self, "경고", "Codeforces 핸들을 입력해주세요.")
            return
        
        self.status_label.setText(f"'{handle}' 님의 레이팅을 조회하는 중...")
        # 별도 스레드에서 레이팅 조회
        thread = threading.Thread(target=self._fetch_and_show_rating, args=(handle,))
        thread.daemon = True
        thread.start()

    # **[추가]** 레이팅 조회 후 시그널을 보내는 실제 로직
    def _fetch_and_show_rating(self, handle):
        rating = self._get_user_rating(handle)
        if rating is not None:
            message = f"'{handle}' 님의 현재 레이팅은 {rating} 입니다."
            self.status_label.setText(f"'{handle}' 님({rating}) | 레이팅 조회가 완료되었습니다.")
        else:
            message = f"'{handle}' 님을 찾을 수 없거나 API 오류가 발생했습니다."
            self.status_label.setText(message)
        
        self.alarm_emitter.rating_info_loaded.emit(message)
    # AlarmApp 클래스 내부에 추가
    def _center_window(self):
        """어플리케이션 창을 화면 중앙에 배치합니다."""
        # 현재 어플리케이션이 실행되는 주 모니터의 가용 영역 정보를 가져옵니다.
        screen_geometry = QApplication.primaryScreen().availableGeometry()
        
        # 현재 윈도우의 사각 영역 정보를 가져옵니다.
        window_geometry = self.frameGeometry()
        
        # 윈도우의 중심점을 화면의 중심점으로 이동시킵니다.
        window_geometry.moveCenter(screen_geometry.center())
        print(screen_geometry.center())
        
        # 윈도우의 좌측 상단 위치를 계산된 위치로 이동시킵니다.
        self.move(window_geometry.topLeft())

def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        # sys._MEIPASS가 없으면, 일반적인 .py 실행 환경임
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    QFontDatabase.addApplicationFont(":/fonts/NotoSansKR-Regular.otf")

    if os.path.exists(resource_path("app_icon.ico")):
        app.setWindowIcon(QIcon(resource_path("app_icon.ico")))

    app.setStyleSheet(ELEGANT_THEME)
    window = AlarmApp()
    window.show()
    sys.exit(app.exec())