# -*- coding: utf-8 -*-


import datetime
import sys
import temp
import pymysql
import serial
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from serial.tools.list_ports import comports




class MainDialog(QDialog, temp.Ui_QDialog):
    def __init__(self):
        QDialog.__init__(self, None)
        self.setupUi(self)

        #----
        self.th_table.setColumnWidth(0, 150)
        self.th_table.setColumnWidth(1, 75)
        self.th_table.setColumnWidth(2, 75)
        self.off_pushButton.clicked.connect(self.off)
        self.on_pushButton.clicked.connect(self.print_data)
        self.on_pushButton.clicked.connect(self.ON)
        self.on_pushButton.clicked.connect(self.save_info)
        self.search_pushButton.clicked.connect(self.avg_calc)
        self.baud_combobox.setCurrentIndex(1)
        self.myTHtimer = QTimer()
        self.Savetimer = QTimer()
        self.myTHtimer.setInterval(1000 * 10)
        self.Savetimer.setInterval(1000 * 60 * 5)
        self.myTHtimer.timeout.connect(self.print_data)
        self.Savetimer.timeout.connect(self.save_info)
        self.check_label.textChanged.connect(self.timer_start)
        self.clear_pushButton.clicked.connect(self.reset_table)
#----


# 현재시간을 문자열로 바꾸는 함수
    def now_time(self):
        now = datetime.datetime.now()
        self.time_lineEdit.setText(now.strftime("%Y-%m-%d %H:%M"))
# on off 탐지후 타이머시작
    def timer_start(self):
        check = self.check_label.text()
        if check == 'ON':
            self.Savetimer.start()
            self.myTHtimer.start()
        else:
            self.Savetimer.stop()
            self.myTHtimer.stop()

#타이머 종료 와 텍스트 초기화하는 함수
    def ON(self):
        a = list(serial.tools.list_ports.comports())
        if a == []:
            self.off()
            QMessageBox.about(self, "Error", "연결된 포트가 없습니다.")
        else:
            self.check_label.setText('ON')

    def off(self):
        self.temp_lineEdit.setText('')
        self.humid_lineEdit.setText('')
        self.time_lineEdit.setText('')
        self.check_label.setText('OFF')


#온도 습도 정보값 수신

    def serial_data(self, TH):
        ExitT = True
        for port, desc, hwid in sorted(comports()):
            port_val = port
        baud_val = self.baud_combobox.currentText()
        ser = serial.Serial(port_val, baud_val)
        STX = 0x02
        ETX = 0x03
        req = 0x31

        check_sum = 48 + 15 - int(chr(req)) - int(chr(TH))
        t_req = bytearray()
        t_req.append(STX)
        t_req.append(req)
        t_req.append(TH)
        t_req.append(check_sum)
        t_req.append(ETX)

        ser.write(t_req)
        temp_val = []
        while ExitT:
            for i in ser.read():
                temp_val.append(i)
                if 3 in temp_val:
                    ExitT = False
                if len(temp_val) > 30:
                    ExitT = False
                    temp_val = []
        self.port_lineEdit.setText(port_val)
        return temp_val

    def data_treatment(self, list):
        if list[0] == 2 and list[5] == 3:
            t_check_num = list[1] + list[2] + list[3] + list[4]
            if t_check_num == 207:
                val = chr(list[2]) + chr(list[3])
            else:
                val = 100
        else:
            val = 100
        return val
# ----------------------------------------------------------------------------------------------------------------
#수신 후 처리 -> 정보값 받기
    count1  = 0
    def data(self):
        global count1
        now = datetime.datetime.now()
        Exitdata = True
        tem_list = self.serial_data(0x30)
        hum_list = self.serial_data(0x31)

        temperature = self.data_treatment(tem_list)
        humid = self.data_treatment(hum_list)
# val = 100 잘못된 값
        while Exitdata:
            if temperature == 100 or humid == 100:
                count1 += 1
                temperature = self.data_treatment(tem_list)
                humid = self.data_treatment(hum_list)
                if count1 == 20:
                    temperature = 'ERROR'
                    humid = 'ERROR'
                    Exitdata = False
            else:
                Exitdata = False
                count1 = 0
        current_time = now.strftime("%Y-%m-%d %H:%M")
        TH_data = [current_time, temperature, humid]
        return TH_data
#시리얼 데이터값으로 라인에딧에 출력
    def print_data(self):
        a = list(serial.tools.list_ports.comports())
        if a == []:
            pass
        else:
            use_data = self.data()
            if use_data[1] == 'ERROR' or use_data[0] == 'ERROR':
                self.print_data()
            else:
                self.time_lineEdit.setText(use_data[0])
                self.temp_lineEdit.setText(use_data[1])
                self.humid_lineEdit.setText(use_data[2])


#현재시간과 받아온 값을 sql 서버에 저장하는 함수
    def save_info(self):
        a = list(serial.tools.list_ports.comports())
        if a == []:
            pass
        else:
            use_data = self.data()
            if use_data[1] == 'ERROR' or use_data[0] == 'ERROR':
                self.save_info()

            else:
                db = pymysql.connect(host='127.0.0.1', port=3306, user='root', password='qwerty123456', db='th_db',
                                     charset='utf8')
                with db:
                    cur = db.cursor()
                    cur.execute("INSERT INTO th_db(Timestamp, temperature, humid)"
                                "VALUES('%s','%s','%s')" % (use_data[0], use_data[1], use_data[2]))



#날짜 입력시 해당 날짜의 데이터 출력
    def avg_calc(self):
        input = self.Q_lineEdit.text()
        value = str(input[:4]) + '-' + str(input[4:6]) + '-' + str(input[6:])
        if len(value) == 10:
            db = pymysql.connect(host='127.0.0.1', port=3306, user='root', password='qwerty123456', db='th_db',
                                 charset='utf8')
            with db:
                cur = db.cursor()
                rows = cur.execute("select Timestamp, temperature, humid from th_db where Timestamp LIKE '{}%'".format(value))
                result = cur.fetchall()
                self.th_table.setRowCount(len(result))
                for i, (time, temperature, humid) in enumerate(result):
                    self.th_table.setItem(i, 0, QTableWidgetItem(time))
                    self.th_table.setItem(i, 1, QTableWidgetItem(temperature))
                    self.th_table.setItem(i, 2, QTableWidgetItem(humid))
                if not result:
                    QMessageBox.about(self, "Error", "값이 없는 날입니다.")
        else:
            QMessageBox.about(self, "Error", "일치하는 형식이 아닙니다.")
#테이블 비우기
    def reset_table(self):
        self.th_table.clearContents()



app = QApplication(sys.argv)
main_dialog = MainDialog()
main_dialog.show()
app.exec_()