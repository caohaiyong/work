#! /usr/bin/python3
import matplotlib.pyplot as plt
import threading
from multiprocessing import Process, Queue
import tkinter as tk
import tkinter.font as tkFont
from tkinter import ttk
import numpy as np
import pandas as pd
import re
import os
import time
import smbus
from pathlib import Path
import pyqtgraph as pg
import array


#动态图点数
PlotNums = 200

#数据默认存储文件
FileName = 'data_record.csv'

#配置文件
LoadTxt = 'regs_cfg_aw9610x.txt'

# 数据寄存器和配置寄存器地址
Raw 			= 0x032c
Lpf 			= 0x0348
Valid 			= 0x026c
Base			= 0x0284
Diff 			= 0x029c
SldData0 		= 0x0224
Sldstat 		= 0x0244
Cmd 			= 0x4408
Irq 			= 0x4410

Wdiff0 			= 0x0584
Wdiff1 			= 0x059c
Wdiff2 			= 0x05b4
Wdiff3 			= 0x05cc
Wdiff4 			= 0x05e4
Wdiff5 			= 0x05fc
Diffset			= 0x0614

# UI控件相关的配置寄存器地址
scanctrl0 		= 0x0000
scanctrl1 		= 0x0004
afecfg0 		= (0x0014,0x0028,0x003c,0x0050,0x0064,0x0078)
#afecfg1 		= (0x0018,0x002c,0x0040,0x0054,0x0068,0x007c)
#afecfg2 		= (0x001c,0x0030,0x0044,0x0058,0x006c,0x0080)
#afecfg3 		= (0x0020,0x0034,0x0048,0x005c,0x0070,0x0084)
#afecfg4 		= (0x0024,0x0038,0x004c,0x0060,0x0074,0x0088)
filtctrl		= (0x008c,0x00cc,0x010c,0x014c,0x018c,0x01cc)
proxth0 		= (0x00b0,0x00f0,0x0130,0x0170,0x01b0,0x01f0)
proxth1 		= (0x00b4,0x00f4,0x0134,0x0174,0x01b4,0x01f4)
proxth2 		= (0x00b8,0x00f8,0x0138,0x0178,0x01b8,0x01f8)
proxth3 		= (0x00bc,0x00fc,0x013c,0x017c,0x01bc,0x01fc)
btnfun 			= (0x00c0,0x0100,0x0140,0x0180,0x01c0,0x0200)
sldcfg0 		= 0x0218
sldcfg1 		= 0x021c
btncfg  		= 0x0220



#将Box中的数据写入芯片
def write_box():
	global Write_addr
	global Write_data
	addr = Write_addr.get()
	data = Write_data.get()
	write_32bit(int(addr,16),int(data,16))

def read_box():
	ft = tkFont.Font(family='Fixdsys',size=15,weight=tkFont.BOLD)
	global Read_addr
	global top
	addr = Read_addr.get()
	data = read_32bit(int(addr,16))
	str_val = tk.StringVar()
	Read_data = tk.Entry(top,textvariable=str_val,font=ft).grid(column=5, row=51)
	str_val.set(data)
	return Read_data


def write_32bit(addr_temp,data_temp):		#  write_32bit(0x10,32),addr=0x0010,data=0x00010000
	global bus
	addr = hex(addr_temp)[2::].zfill(4)
	data = hex(data_temp)[2::].zfill(8)
	bus.write_i2c_block_data(0x12,int(addr[0:2],16),[int(addr[2:4],16),int(data[0:2],16),int(data[2:4],16),int(data[4:6],16),int(data[6:8],16)])


def read_32bit(addr_temp,format=1):		#  read_32bit(0x0210,1),format=0/1/2决定返回值格式
	global bus
	addr = hex(addr_temp)[2::].zfill(4)	#小心顺序！ 0x02 is addr[0:2];0x10 is addr[2:4]
	bus.write_byte_data(0x12,int(addr[0:2],16),int(addr[2:4],16))
	list_temp = bus.read_i2c_block_data(0x12,int(addr[0:2],16),4)
	temp1 = list_temp[0]<<24
	temp2 = list_temp[1]<<16
	temp3 = list_temp[2]<<8
	temp4 = list_temp[3]
	temp = temp1+temp2+temp3+temp4	#y= x<<1 + x 切记不等于3x 这种写法每次移位都会带来x的改变，即移位操作会更新变量,并带入后续计算
	if format == 0:
		if temp < 2**31:
			data_temp = temp/1024 
		else:
			data_temp = (temp-2**32)/1024 		
		data_temp = int(data_temp)	#返回有符号整数,动态绘图时使用
	elif format == 1:
		data_temp = '0x'+hex(temp)[2::].zfill(8)	#返回16进制字符串,存入文本时使用该格式
	else:
		data_temp = bin(temp)[2::].zfill(32)	#返回32bit的2进制字符串,方便提取返回值的若干位进行判断
	return data_temp


def read_8word(addr_temp,nums,format=1):		#  read_8word(0x004,8),read 8 words data,8 is maximum
	global bus
	data = []
	addr = hex(addr_temp)[2::].zfill(4)
	bus.write_byte_data(0x12,int(addr[0:2],16),int(addr[2:4],16))
	list_temp = bus.read_i2c_block_data(0x12,int(addr[0:2],16),nums<<2)
	for i in range(nums<<2):
		if i%4 == 3:
			temp1 = list_temp[i-3]<<24
			temp2 = list_temp[i-2]<<16
			temp3 = list_temp[i-1]<<8
			temp4 = list_temp[i]
			temp = temp1+temp2+temp3+temp4
			if format == 0:
				if temp < 2**31:
					data_temp = temp/1024 
				else:
					data_temp = (temp-2**32)/1024 		
				data.append(int(data_temp))
			elif format == 1:
				data_temp = '0x'+hex(temp)[2::].zfill(8)
				data.append(data_temp)
			else:
				data_temp = bin(temp)[2::].zfill(32)
				data.append(data_temp)
	return data
	

def StaticPlot(style):			
	#选择绘图类型，raw或者diff等等
	Raw = ['raw0','raw1','raw2','raw3','raw4','raw5']
	Valid = ['valid0','valid1','valid2','valid3','valid4','valid5']
	Base = ['base0','base1','base2','base3','base4','base5']
	Diff = ['diff0','diff1','diff2','diff3','diff4','diff5']
	Pos = ['position','diffoffset','posoffset','movedistance','slidetouch']
	dict = {'raw':Raw,'valid':Valid,'base':Base,'diff':Diff,'position':Pos}
	temp = dict.get(style,'ErrorStyle')
	data = pd.read_csv(FileName)
	data = np.array(data.loc[:,temp])
	#绘图
	if style == 'position':
		plt.figure(style)
		plt.plot(data[:,0],'r-o',data[:,1],'g-o',data[:,2],'b-o',data[:,3],'m-o',data[:,4],'y-o') 
		plt.legend(['Position','DiffOffset','PosOffset','MoveDistance','SliderTouchST'])
		plt.ylabel('Value')
		plt.xlabel('Sample (N)')
		plt.grid()
	else:
		plt.figure(style)
		plt.plot(data[:,0], 'r-o',data[:,1],'g-o',data[:,2],'b-o',data[:,3],'m-o',data[:,4],'y-o',data[:,5],'k-o') 
		plt.legend(['CS0','CS1','CS2','CS3','CS4','CS5'],loc='best')
		plt.ylabel('Value')
		plt.xlabel('Sample (N)')
		plt.grid()


def splot_raw():	#多线程，不要堵塞主程序
	StaticPlot('raw')
	plt.show()
	#threading.Thread(target=StaticPlot,args=('raw',)).start()

def splot_valid():
	StaticPlot('valid')
	plt.show()

def splot_base():
	StaticPlot('base')
	plt.show()

def splot_diff():
	StaticPlot('diff')
	plt.show()

def splot_position():
	StaticPlot('position')
	plt.show()

	
# 将寄存器配置值写入txt文件中
def write_txt(filename,addr,data,msb,lsb):
	file_data = ''
	addr_temp = '0x' + hex(addr)[2::].zfill(4)
	with open(filename,"r",encoding="utf-8") as f:
		for line in f:
			if (addr_temp+',') in line:
				temp = re.findall(r'0x[0-9a-zA-Z]{8}',line)
				temp = int(temp[0],16)
				temp1 = (temp >> (msb+1)) << (msb+1)
				temp2 = data << lsb
				temp3 = temp % (2**lsb)   
				temp = temp1 + temp2 + temp3
				#temp = (temp >> (msb+1)) << (msb+1) + data << lsb + temp % (2**lsb)   # this is error!!! temp will change during calculate
				temp = hex(temp)			#0x2c
				temp = temp[2:]  			#2c
				temp = '0x'+ temp.zfill(8)  #0x0000002c
				line = re.sub(r'0x[0-9a-zA-Z]{8}',temp,line,flags=0) #将原有数据替换为新数据
			file_data = file_data+line
	with open(filename,"w",encoding="utf-8") as f:
		f.write(file_data)


# 保存数据到txt的线程,可以暂停/继续/重启
class SaveData1(threading.Thread):
	def __init__(self):
		#super().__init__()
		threading.Thread.__init__(self)
		self.__flag = threading.Event()     # 用于暂停线程的标识
		self.__flag.set()       			# 设置为True
		self.__running = threading.Event()  # 用于停止线程的标识
		self.__running.set()      			# 将running设置为True

	def run(self):
		firstline = ['wdiff00,','wdiff01,','wdiff02,','wdiff03,','wdiff04,','wdiff05,','wdiff10,','wdiff11,','wdiff12,','wdiff13,','wdiff14,','wdiff15,','wdiff20,','wdiff21,','wdiff22,','wdiff23,','wdiff24,','wdiff25,','wdiff30,','wdiff31,','wdiff32,','wdiff33,','wdiff34,','wdiff35,','wdiff40,','wdiff41,','wdiff42,','wdiff43,','wdiff44,','wdiff45,','wdiff50,','wdiff51,','wdiff52,','wdiff53,','wdiff54,','wdiff55,','diff0,','diff1,','diff2,','diff3,','diff4,','diff5,','position,','diffoffset,','posoffset,','movedistance,','slidetouch,','diffset0,','diffset1,','diffset2,','diffset3,','diffset4,','diffset5,']
		with open(FileName,"w+",encoding="utf-8") as f:
			f.writelines(firstline)
		while self.__running.isSet():
			self.__flag.wait()      # 为True时立即返回, 为False时阻塞直到self.__flag为True后返回
			#print(time.time()-pretime)
			#pretime = time.time()
			wdiff0 	= read_8word(Wdiff0,6,format=0)
			wdiff1 	= read_8word(Wdiff1,6,format=0)
			wdiff2 	= read_8word(Wdiff2,6,format=0)
			wdiff3 	= read_8word(Wdiff3,6,format=0)
			wdiff4 	= read_8word(Wdiff4,6,format=0)
			wdiff5 	= read_8word(Wdiff5,6,format=0)
			diffset	= read_8word(Diffset,6,format=0)
			diff 	= read_8word(Diff,6,format=0)
			sld  	= read_8word(SldData0,2,format=2)
			ST 		= read_8word(Sldstat,3,format=2)
			irq 	= read_32bit(Irq,format=2)
			pos 	= [int(sld[0][24:32],2),int(sld[1][8:16],2),int(sld[1][16:24],2),int(sld[1][24:32],2),int(ST[0][1],2)*10]
			if(int(irq[19:22],2)):	# 当发生TWS中断时，把对应的中断事件状态打印到终端
				#print(time.time())
				print("SingleClick=%s,DoubleClick=%s,TrebleClick=%s,Press=%s,LongPress=%s,NormSlide=%s,ConSlide=%s,Irq=%s" %(ST[2][25:32],ST[2][17:24],ST[2][9:16],ST[1][25:32],ST[1][17:24],ST[0][29:32],ST[0][22:24],irq[19:22]))
			temp = wdiff0+wdiff1+wdiff2+wdiff3+wdiff4+wdiff5+diff+pos+diffset
			temp = [str(i)+',' for i in temp]
			with open(FileName,"a+",encoding="utf-8") as f:
				f.writelines('\n')
				f.writelines(temp)

	def pause(self):
		self.__flag.clear()     #设置为False, 让线程阻塞

	def resume(self):
		self.__flag.set()    	#设置为True, 让线程停止阻塞

	def stop(self):
		self.__flag.set()       #将线程从暂停状态恢复, 如何已经暂停的话
		self.__running.clear()	#设置为False,让线程停止

class SaveData(threading.Thread):
	def __init__(self):
		#super().__init__()
		threading.Thread.__init__(self)
		self.__flag = threading.Event()     # 用于暂停线程的标识
		self.__flag.set()       			# 设置为True
		self.__running = threading.Event()  # 用于停止线程的标识
		self.__running.set()      			# 将running设置为True

	def run(self):
		#pretime = time.time()
		firstline = ['raw0,','raw1,','raw2,','raw3,','raw4,','raw5,','valid0,','valid1,','valid2,','valid3,','valid4,','valid5,','base0,','base1,','base2,','base3,','base4,','base5,','diff0,','diff1,','diff2,','diff3,','diff4,','diff5,','position,','diffoffset,','posoffset,','movedistance,','slidetouch,']
		with open(FileName,"w+",encoding="utf-8") as f:
			f.writelines(firstline)
		while self.__running.isSet():
			self.__flag.wait()      # 为True时立即返回, 为False时阻塞直到self.__flag为True后返回
			#print(time.time()-pretime)
			#pretime = time.time()
			raw 	= read_8word(Raw,6,format=0)
			valid 	= read_8word(Valid,6,format=0)
			base 	= read_8word(Base,6,format=0)
			diff 	= read_8word(Diff,6,format=0)
			sld  	= read_8word(SldData0,2,format=2)
			ST 		= read_8word(Sldstat,3,format=2)
			irq 	= read_32bit(Irq,format=2)
			pos 	= [int(sld[0][24:32],2),int(sld[1][8:16],2),int(sld[1][16:24],2),int(sld[1][24:32],2),int(ST[0][1],2)*10]
			if(int(irq[19:22],2)):	# 当发生TWS中断时，把对应的中断事件状态打印到终端
				#print(time.time())
				print("SingleClick=%s,DoubleClick=%s,TrebleClick=%s,Press=%s,LongPress=%s,NormSlide=%s,ConSlide=%s,Irq=%s" %(ST[2][25:32],ST[2][17:24],ST[2][9:16],ST[1][25:32],ST[1][17:24],ST[0][29:32],ST[0][22:24],irq[19:22]))
			temp = raw+valid+base+diff+pos
			temp = [str(i)+',' for i in temp]
			with open(FileName,"a+",encoding="utf-8") as f:
				f.writelines('\n')
				f.writelines(temp)

	def pause(self):
		self.__flag.clear()     #设置为False, 让线程阻塞

	def resume(self):
		self.__flag.set()    	#设置为True, 让线程停止阻塞

	def stop(self):
		self.__flag.set()       #将线程从暂停状态恢复, 如何已经暂停的话
		self.__running.clear()	#设置为False,让线程停止


# 如果保存数据的线程仍然存在，则让其停止，并重新创建一个保存数据的线程，根据python的垃圾回收机制，线程停止后，该线程的所有资源均被回收
def save_data():	
	global p1
	if p1.is_alive():
		p1.stop()
	time.sleep(0.1)
	p1 = SaveData()	#不能直接使用对象中的消息绑定任何事件动作,因为事件动作会执行初始化，会导致消息直接运行
	p1.start()

def stop_save():
	global p1
	p1.pause()

def resume_save():
	global p1
	p1.resume()

#采集数据并实时绘图
def plotData():
	global idx#内部作用域想改变外部域变量
	global pretime
	global plotdata
	global curve0,curve1,curve2,curve3,curve4,curve5
	#print(time.time()-pretime)
	#pretime = time.time()
	raw 	= read_8word(Raw,6,format=0)
	valid 	= read_8word(Valid,6,format=0)
	base 	= read_8word(Base,6,format=0)
	diff 	= read_8word(Diff,6,format=0)
	irq 	= read_32bit(Irq,format=2)
	ST 		= read_8word(Sldstat,3,format=2)
	if(int(irq[19:22],2)):	# 当发生TWS中断时，把对应的中断事件状态打印到终端
		print("SingleClick=%s,DoubleClick=%s,TrebleClick=%s,Press=%s,LongPress=%s,NormSlide=%s,ConSlide=%s" %(ST[2][25:32],ST[2][17:24],ST[2][9:16],ST[1][25:32],ST[1][17:24],ST[0][29:32],ST[0][22:24]))
	#绘制CH0～CH5的动态图
	if len(plotdata[0])<PlotNums:
		plotdata[0].append(raw[0]) #raw[0]
		plotdata[1].append(raw[1]) #raw[0]
		plotdata[2].append(raw[2]) #raw[0]
		plotdata[3].append(raw[3]) #raw[0]
		plotdata[4].append(raw[4]) #raw[0]
		plotdata[5].append(raw[5]) #raw[0]
	else:
		plotdata[0][:-1] = plotdata[0][1:]#前移,[-1]表示列表的倒数第一个元素
		plotdata[0][-1] = raw[0]     
		plotdata[1][:-1] = plotdata[1][1:]#前移,[-1]表示列表的倒数第一个元素
		plotdata[1][-1] = raw[1]     
		plotdata[2][:-1] = plotdata[2][1:]#前移,[-1]表示列表的倒数第一个元素
		plotdata[2][-1] = raw[2]     
		plotdata[3][:-1] = plotdata[3][1:]#前移,[-1]表示列表的倒数第一个元素
		plotdata[3][-1] = raw[3]     
		plotdata[4][:-1] = plotdata[4][1:]#前移,[-1]表示列表的倒数第一个元素
		plotdata[4][-1] = raw[4]     
		plotdata[5][:-1] = plotdata[5][1:]#前移,[-1]表示列表的倒数第一个元素
		plotdata[5][-1] = raw[5]
	curve0.setData(plotdata[0])
	curve1.setData(plotdata[1])
	curve2.setData(plotdata[2])
	curve3.setData(plotdata[3])
	curve4.setData(plotdata[4])
	curve5.setData(plotdata[5])
	idx = idx + 1
	#print(time.time()-pretime)


def dplot_raw():	#该线程会堵塞主程序，直到该app退出
	global idx
	global pretime
	global plotdata
	global curve0,curve1,curve2,curve3,curve4,curve5
	idx = 0;pretime = 0;plotdata = [[],[],[],[],[],[]]
	#创建绘图app并执行
	app = pg.mkQApp()#建立app
	win = pg.GraphicsWindow()#建立窗口
	win.setWindowTitle(u'动态绘图')
	win.resize(1800, 1000)#小窗口大小
	p = win.addPlot(left='',bootom='',title='Raw实时数据')#把图p加入到窗口中
	p.showGrid(x=True, y=True)#把X和Y的表格打开
	p.setRange(xRange=[0,PlotNums],padding=0)
	curve0 = p.plot(pen='r')#绘制一个图形
	curve1 = p.plot(pen='g')#绘制一个图形
	curve2 = p.plot(pen='b')#绘制一个图形
	curve3 = p.plot(pen='w')#绘制一个图形
	curve4 = p.plot(pen='y')#绘制一个图形
	curve5 = p.plot(pen='m')#绘制一个图形
	timer = pg.QtCore.QTimer()
	timer.timeout.connect(plotData)#定时调用plotData函数
	timer.start(50)#多少ms调用一次
	app.exec_()


def config_reg():
	with open(LoadTxt,"r",encoding="utf-8") as f:
		for line in f:
			temp = re.findall(r'0x[0-9a-zA-Z]{4,8}',line)
			addr = temp[0]
			data = temp[1]
			write_32bit(int(addr,16),int(data,16))
	print('The Registers Config Finshed !')


def read_reg():
	with open(LoadTxt,"r",encoding="utf-8") as f:
		for line in f:
			temp = re.findall(r'0x[0-9a-zA-Z]{4,8}',line)
			addr = temp[0]
			data = read_32bit(int(addr,16))
			print('%s,%s' %(temp[0],data))

def update_reg():
	global my_Aox;global my_Box;global my_Cox;global my_Dox;global my_Eox;global my_Fox;global my_Gox;global my_Hox;
	for i in my_Aox:
		i.update_config()
	for i in my_Box:
		i.update_config()
	for i in my_Cox:
		i.update_config()
	for i in my_Dox:
		i.update_config()
	for i in my_Eox:
		i.update_config()
	for i in my_Fox:
		i.update_config()
	for i in my_Gox:
		i.update_config()
	for i in my_Hox:
		i.update_config()
	print('The UI Registers Update Finshed !')


def active():
	write_32bit(Cmd,0x1)
	#os.system('i2ctransfer -y 1 w6@0x12 0x44 0x08 0x00 0x00 0x00 0x01')
	#其返回值是shell指令运行后返回的状态码，int类型，0表示shell指令成功执行
	print('Active Mode!')

def sleep():
	write_32bit(Cmd,0x2)
	print('Sleep Mode!')

def correct():
	temp = os.popen('i2ctransfer -y 1 w2@0x12 0x00 0x00 r4 | awk \'{print $4}\'').read()	#读取0x0000地址的最低byte并赋值给temp
	temp = temp[2:]
	command = 'i2ctransfer -y 1 w6@0x12 0x00 0x00 0x00 0x00 0xff 0x'+ temp.zfill(2)
	os.system(command)
	print('Correct Finshed !')


class ui_inst():
	def __init__(self,window,name,addr,msb,lsb,val,row,col):
		self.window = window
		self.name = name	# 寄存器名称
		self.addr = addr	# 寄存器地址
		self.msb = msb		# 寄存器最高位
		self.lsb = lsb		# 寄存器最低位
		self.val = val		# 下拉列表
		self.row = row		# 控件所在位置
		self.col = col		# 控件所在位置

	def set_init_window(self):
		ft = tkFont.Font(family='Fixdsys',size=15,weight=tkFont.BOLD)
		self.combox = ttk.Combobox(self.window, width=12,font=ft)
		self.combox['values'] = self.val     					# 设置下拉列表的值
		self.combox.grid(column=self.col, row=self.row+1)      	# 设置其在界面中出现的位置 column代表列 row 代表行
		#self.combox.current(0)    								# 设置下拉列表默认显示的值，0为 numberChosen['values'] 的下标值
		self.combox.bind("<<ComboboxSelected>>",self.action)
		tk.Label(self.window,text=self.name,font=ft).grid(column=self.col,row=self.row)
	
	def update_config(self):
		data = read_32bit(self.addr,format=2)
		temp = data[31-self.msb:31-self.lsb+1]
		temp = hex(int(temp,2))[2::]
		pattern = re.compile(r'^'+temp+'(.+)$')
		for i in self.val:
			m1 = re.match(pattern,i)
			if m1:
				self.combox.current(self.val.index(i))
				break

	def action(self,event):
		s=self.combox.get()
		a=s.split('(')
		write_txt('regs_cfg_aw9610x.txt',self.addr,int(a[0],16),self.msb,self.lsb)



def main():
	#保存数据线程和动态画图线程
	global p1
	p1 = SaveData()	#不能直接使用对象中的消息绑定任何事件动作,因为事件动作会执行初始化，会导致消息直接运行
	global my_Aox;global my_Box;global my_Cox;global my_Dox;global my_Eox;global my_Fox;global my_Gox;global my_Hox;

	#UI界面
	global top
	top = tk.Tk()
	top.title("A1913 UI")    # 添加标题

	#读写寄存器控件
	global bus
	bus = smbus.SMBus(1)
	ft = tkFont.Font(family='Fixdsys',size=15,weight=tkFont.BOLD)
	global Write_addr
	Write_addr = tk.Entry(font=ft)
	Write_addr.grid(column=4, row=50)
	global Write_data
	Write_data = tk.Entry(font=ft)
	Write_data.grid(column=5, row=50)
	global Read_addr
	Read_addr = tk.Entry(font=ft)
	Read_addr.grid(column=4, row=51)
	Write_Word = tk.Button(top,text='Write!',bg="lightblue", width=10,font=ft,command=write_box).grid(column=6, row=50)
	Read_Word = tk.Button(top,text='Read!',bg="lightblue", width=10,font=ft,command=read_box).grid(column=6, row=51)

	#画图
	#btn1 = tk.Button(top,text='PlotStop',width=10,font=ft,command=dplot_stop).grid(column=6,row=52)
	btn2 = tk.Button(top,text='继续',width=10,font=ft,command=resume_save).grid(column=4,row=52)
	btn3 = tk.Button(top,text='暂停',width=10,font=ft,command=stop_save).grid(column=3,row=52)


	#全局寄存器相关控件
	Aox1  = ui_inst(top,'ScanPeriod',scanctrl1,10,0,[hex(i)[2::]+'('+str(i*2)+'ms)' for i in range(256)],1,3)
	my_Aox = [Aox1]
	for i in my_Aox:
		i.set_init_window()	#()必须要加
		i.update_config()

	# CH0配置寄存器相关控件
	Box1 = ui_inst(top,'CH0_EN',scanctrl0,0,0,('0(NO)','1(YES)'),3,1)
	Box2 = ui_inst(top,'SelCS0',afecfg0[0],11,0,('0(None)','1(HZ)','aa9(SHD)','ffd(GND)'),3,2)
	Box3 = ui_inst(top,'Cfb&Res',afecfg0[0],19,12,('0(0)','53(32Res,4.4pF)','83(256Res,4.4pF)','56(32Res,8.8pF)','86(256Res,8.8pF)'),3,3)
	Box4 = ui_inst(top,'SampNum',filtctrl[0],26,25,('0(1)','1(2)','2(4)','3(8)'),3,4)
	Box5 = ui_inst(top,'ProxTh0',proxth0[0],20,0,('0(0)','4e20(2万)','7530(3万)','9c40(4万)','c350(5万)','ea60(6万)','13880(8万)'),3,5)
	Box6 = ui_inst(top,'ProxTh1',proxth1[0],20,0,('0(0)','c350(5万)','ea60(6万)','13880(8万)','186a0(10万)','249f0(15万)'),3,6)
	Box7 = ui_inst(top,'ProxTh2',proxth2[0],20,0,('0(0)','186a0(10万)','249f0(15万)','30d40(20万)','493e0(30万)','61a80(40万)'),3,7)
	Box8 = ui_inst(top,'ProxTh3',proxth3[0],20,0,('0(0)','61a80(40万)','7a120(50万)','927c0(60万)','aae60(70万)','c3500(80万)'),5,7)
	Box9 = ui_inst(top,'WearEn&BtnEn',btnfun[0],31,30,('0(NO)','1(BtnEn)','2(WearEn)'),5,2)
	Box10 = ui_inst(top,'SoftWearTh',btnfun[0],13,12,('0(ProxTH0)','1(ProxTH1)','2(ProxTH2)','3(ProxTH3)'),5,3)
	Box11 = ui_inst(top,'HardWearTh',btnfun[0],11,10,('0(ProxTH0)','1(ProxTH1)','2(ProxTH2)','3(ProxTH3)'),5,4)
	Box12 = ui_inst(top,'BtnTouchTh',btnfun[0],9,8,('0(ProxTH0)','1(ProxTH1)','2(ProxTH2)','3(ProxTH3)'),5,5)
	Box13 = ui_inst(top,'BtnFunSel',btnfun[0],4,0,[hex(i)[2::]+'('+str(i)+')' for i in range(32)],5,6)
	my_Box = [Box1,Box2,Box3,Box4,Box5,Box6,Box7,Box8,Box9,Box10,Box11,Box12,Box13]
	for i in my_Box:
		i.set_init_window()	#()必须要加
		i.update_config()

	#CH1配置寄存器
	Cox1 = ui_inst(top,'CH1_EN', scanctrl0,1,1,('0(NO)','1(YES)'),7,1)
	Cox2 = ui_inst(top,'SelCS1', afecfg0[1],11,0,('0(None)','4(HZ)','aa6(SHD)','ff7(GND)'),7,2)
	Cox3 = ui_inst(top,'Cfb&Res',afecfg0[1],19,12,('0(0)','53(32Res,4.4pF)','83(256Res,4.4pF)','56(32Res,8.8pF)','86(256Res,8.8pF)'),7,3)
	Cox4 = ui_inst(top,'SampNum',filtctrl[1],26,25,('0(1)','1(2)','2(4)','3(8)'),7,4)
	Cox5 = ui_inst(top,'ProxTh0',proxth0[1],20,0,('0(0)','4e20(2万)','7530(3万)','9c40(4万)','c350(5万)','ea60(6万)','13880(8万)'),7,5)
	Cox6 = ui_inst(top,'ProxTh1',proxth1[1],20,0,('0(0)','c350(5万)','ea60(6万)','13880(8万)','186a0(10万)','249f0(15万)'),7,6)
	Cox7 = ui_inst(top,'ProxTh2',proxth2[1],20,0,('0(0)','186a0(10万)','249f0(15万)','30d40(20万)','493e0(30万)','61a80(40万)'),7,7)
	Cox8 = ui_inst(top,'ProxTh3',proxth3[1],20,0,('0(0)','61a80(40万)','7a120(50万)','927c0(60万)','aae60(70万)','c3500(80万)'),9,7)
	Cox9 = ui_inst(top,'WearEn&BtnEn',btnfun[1],31,30,('0(NO)','1(BtnEn)','2(WearEn)'),9,2)
	Cox10 = ui_inst(top,'SoftWearTh',btnfun[1],13,12,('0(ProxTH0)','1(ProxTH1)','2(ProxTH2)','3(ProxTH3)'),9,3)
	Cox11 = ui_inst(top,'HardWearTh',btnfun[1],11,10,('0(ProxTH0)','1(ProxTH1)','2(ProxTH2)','3(ProxTH3)'),9,4)
	Cox12 = ui_inst(top,'BtnTouchTh',btnfun[1],9,8,('0(ProxTH0)','1(ProxTH1)','2(ProxTH2)','3(ProxTH3)'),9,5)
	Cox13 = ui_inst(top,'BtnFun',btnfun[1],4,0,[hex(i)[2::]+'('+str(i)+')' for i in range(32)],9,6)
	my_Cox = [Cox1,Cox2,Cox3,Cox4,Cox5,Cox6,Cox7,Cox8,Cox9,Cox10,Cox11,Cox12,Cox13]
	for i in my_Cox:
		i.set_init_window()
		i.update_config()

	#CH2配置寄存器
	Dox1  = ui_inst(top,'CH2_EN',scanctrl0,2,2,('0(NO)','1(YES)'),11,1)
	Dox2 = ui_inst(top,'SelCS2', afecfg0[2],11,0,('0(None)','10(HZ)','a9a(SHD)','fdf(GND)'),11,2)
	Dox3 = ui_inst(top,'Cfb&Res',afecfg0[2],19,12,('0(0)','53(32Res,4.4pF)','83(256Res,4.4pF)','56(32Res,8.8pF)','86(256Res,8.8pF)'),11,3)
	Dox4 = ui_inst(top,'SampNum',filtctrl[2],26,25,('0(1)','1(2)','2(4)','3(8)'),11,4)
	Dox5 = ui_inst(top,'ProxTh0',proxth0[2],20,0,('0(0)','4e20(2万)','7530(3万)','9c40(4万)','c350(5万)','ea60(6万)','13880(8万)'),11,5)
	Dox6 = ui_inst(top,'ProxTh1',proxth1[2],20,0,('0(0)','c350(5万)','ea60(6万)','13880(8万)','186a0(10万)','249f0(15万)'),11,6)
	Dox7 = ui_inst(top,'ProxTh2',proxth2[2],20,0,('0(0)','186a0(10万)','249f0(15万)','30d40(20万)','493e0(30万)','61a80(40万)'),11,7)
	Dox8 = ui_inst(top,'ProxTh3',proxth3[2],20,0,('0(0)','61a80(40万)','7a120(50万)','927c0(60万)','aae60(70万)','c3500(80万)'),13,7)
	Dox9 = ui_inst(top,'WearEn&BtnEn',btnfun[2],31,30,('0(NO)','1(BtnEn)','2(WearEn)'),13,2)
	Dox10 = ui_inst(top,'SoftWearTh',btnfun[2],13,12,('0(ProxTH0)','1(ProxTH1)','2(ProxTH2)','3(ProxTH3)'),13,3)
	Dox11 = ui_inst(top,'HardWearTh',btnfun[2],11,10,('0(ProxTH0)','1(ProxTH1)','2(ProxTH2)','3(ProxTH3)'),13,4)
	Dox12 = ui_inst(top,'BtnTouchTh',btnfun[2],9,8,('0(ProxTH0)','1(ProxTH1)','2(ProxTH2)','3(ProxTH3)'),13,5)
	Dox13 = ui_inst(top,'BtnFun',btnfun[2],4,0,[hex(i)[2::]+'('+str(i)+')' for i in range(32)],13,6)
	my_Dox = [Dox1,Dox2,Dox3,Dox4,Dox5,Dox6,Dox7,Dox8,Dox9,Dox10,Dox11,Dox12,Dox13]
	for i in my_Dox:
		i.set_init_window()
		i.update_config()

	#CH3配置寄存器
	Eox1  = ui_inst(top,'CH3_EN',scanctrl0,3,3,('0(NO)','1(YES)'),16,1)
	Eox2 = ui_inst(top,'SelCS3', afecfg0[3],11,0,('0(None)','40(HZ)','a6a(SHD)','f7f(GND)'),16,2)
	Eox3 = ui_inst(top,'Cfb&Res',afecfg0[3],19,12,('0(0)','53(32Res,4.4pF)','83(256Res,4.4pF)','56(32Res,8.8pF)','86(256Res,8.8pF)'),16,3)
	Eox4 = ui_inst(top,'SampNum',filtctrl[3],26,25,('0(1)','1(2)','2(4)','3(8)'),16,4)
	Eox5 = ui_inst(top,'ProxTh0',proxth0[3],20,0,('0(0)','4e20(2万)','7530(3万)','9c40(4万)','c350(5万)','ea60(6万)','13880(8万)'),16,5)
	Eox6 = ui_inst(top,'ProxTh1',proxth1[3],20,0,('0(0)','c350(5万)','ea60(6万)','13880(8万)','186a0(10万)','249f0(15万)'),16,6)
	Eox7 = ui_inst(top,'ProxTh2',proxth2[3],20,0,('0(0)','186a0(10万)','249f0(15万)','30d40(20万)','493e0(30万)','61a80(40万)'),16,7)
	Eox8 = ui_inst(top,'ProxTh3',proxth3[3],20,0,('0(0)','61a80(40万)','7a120(50万)','927c0(60万)','aae60(70万)','c3500(80万)'),18,7)
	Eox9 = ui_inst(top,'WearEn&BtnEn',btnfun[3],31,30,('0(NO)','1(BtnEn)','2(WearEn)'),18,2)
	Eox10 = ui_inst(top,'SoftWearTh',btnfun[3],13,12,('0(ProxTH0)','1(ProxTH1)','2(ProxTH2)','3(ProxTH3)'),18,3)
	Eox11 = ui_inst(top,'HardWearTh',btnfun[3],11,10,('0(ProxTH0)','1(ProxTH1)','2(ProxTH2)','3(ProxTH3)'),18,4)
	Eox12 = ui_inst(top,'BtnTouchTh',btnfun[3],9,8,('0(ProxTH0)','1(ProxTH1)','2(ProxTH2)','3(ProxTH3)'),18,5)
	Eox13 = ui_inst(top,'BtnFun',btnfun[3],4,0,[hex(i)[2::]+'('+str(i)+')' for i in range(32)],18,6)
	my_Eox = [Eox1,Eox2,Eox3,Eox4,Eox5,Eox6,Eox7,Eox8,Eox9,Eox10,Eox11,Eox12,Eox13]
	for i in my_Eox:
		i.set_init_window()
		i.update_config()

	#CH4配置寄存器
	Fox1  = ui_inst(top,'CH4_EN',scanctrl0,4,4,('0(NO)','1(YES)'),21,1)
	Fox2 = ui_inst(top,'SelCS4', afecfg0[4],11,0,('0(None)','100(HZ)','9aa(SHD)','dff(GND)'),21,2)
	Fox3 = ui_inst(top,'Cfb&Res',afecfg0[4],19,12,('0(0)','53(32Res,4.4pF)','83(256Res,4.4pF)','56(32Res,8.8pF)','86(256Res,8.8pF)'),21,3)
	Fox4 = ui_inst(top,'SampNum',filtctrl[4],26,25,('0(1)','1(2)','2(4)','3(8)'),21,4)
	Fox5 = ui_inst(top,'ProxTh0',proxth0[4],20,0,('0(0)','4e20(2万)','7530(3万)','9c40(4万)','c350(5万)','ea60(6万)','13880(8万)'),21,5)
	Fox6 = ui_inst(top,'ProxTh1',proxth1[4],20,0,('0(0)','c350(5万)','ea60(6万)','13880(8万)','186a0(10万)','249f0(15万)'),21,6)
	Fox7 = ui_inst(top,'ProxTh2',proxth2[4],20,0,('0(0)','186a0(10万)','249f0(15万)','30d40(20万)','493e0(30万)','61a80(40万)'),21,7)
	Fox8 = ui_inst(top,'ProxTh3',proxth3[4],20,0,('0(0)','61a80(40万)','7a120(50万)','927c0(60万)','aae60(70万)','c3500(80万)'),23,7)
	Fox9 = ui_inst(top,'WearEn&BtnEn',btnfun[4],31,30,('0(NO)','1(BtnEn)','2(WearEn)'),23,2)
	Fox10 = ui_inst(top,'SoftWearTh',btnfun[4],13,12,('0(ProxTH0)','1(ProxTH1)','2(ProxTH2)','3(ProxTH3)'),23,3)
	Fox11 = ui_inst(top,'HardWearTh',btnfun[4],11,10,('0(ProxTH0)','1(ProxTH1)','2(ProxTH2)','3(ProxTH3)'),23,4)
	Fox12 = ui_inst(top,'BtnTouchTh',btnfun[4],9,8,('0(ProxTH0)','1(ProxTH1)','2(ProxTH2)','3(ProxTH3)'),23,5)
	Fox13 = ui_inst(top,'BtnFun',btnfun[4],4,0,[hex(i)[2::]+'('+str(i)+')' for i in range(32)],23,6)
	my_Fox = [Fox1,Fox2,Fox3,Fox4,Fox5,Fox6,Fox7,Fox8,Fox9,Fox10,Fox11,Fox12,Fox13]
	for i in my_Fox:
		i.set_init_window()
		i.update_config()

	#CH5配置寄存器
	Gox1  = ui_inst(top,'CH5_EN',scanctrl0,5,5,('0(NO)','1(YES)'),26,1)
	Gox2 = ui_inst(top,'SelCS5', afecfg0[5],11,0,('0(None)','400(HZ)','6aa(SHD)','7ff(GND)'),26,2)
	Gox3 = ui_inst(top,'Cfb&Res',afecfg0[5],19,12,('0(0)','53(32Res,4.4pF)','83(256Res,4.4pF)','56(32Res,8.8pF)','86(256Res,8.8pF)'),26,3)
	Gox4 = ui_inst(top,'SampNum',filtctrl[5],26,25,('0(1)','1(2)','2(4)','3(8)'),26,4)
	Gox5 = ui_inst(top,'ProxTh0',proxth0[5],20,0,('0(0)','4e20(2万)','7530(3万)','9c40(4万)','c350(5万)','ea60(6万)','13880(8万)'),26,5)
	Gox6 = ui_inst(top,'ProxTh1',proxth1[5],20,0,('0(0)','c350(5万)','ea60(6万)','13880(8万)','186a0(10万)','249f0(15万)'),26,6)
	Gox7 = ui_inst(top,'ProxTh2',proxth2[5],20,0,('0(0)','186a0(10万)','249f0(15万)','30d40(20万)','493e0(30万)','61a80(40万)'),26,7)
	Gox8 = ui_inst(top,'ProxTh3',proxth3[5],20,0,('0(0)','61a80(40万)','7a120(50万)','927c0(60万)','aae60(70万)','c3500(80万)'),28,7)
	Gox9 = ui_inst(top,'WearEn&BtnEn',btnfun[5],31,30,('0(NO)','1(BtnEn)','2(WearEn)'),28,2)
	Gox10 = ui_inst(top,'SoftWearTh',btnfun[5],13,12,('0(ProxTH0)','1(ProxTH1)','2(ProxTH2)','3(ProxTH3)'),28,3)
	Gox11 = ui_inst(top,'HardWearTh',btnfun[5],11,10,('0(ProxTH0)','1(ProxTH1)','2(ProxTH2)','3(ProxTH3)'),28,4)
	Gox12 = ui_inst(top,'BtnTouchTh',btnfun[5],9,8,('0(ProxTH0)','1(ProxTH1)','2(ProxTH2)','3(ProxTH3)'),28,5)
	Gox13 = ui_inst(top,'BtnFun',btnfun[5],4,0,[hex(i)[2::]+'('+str(i)+')' for i in range(32)],28,6)
	my_Gox = [Gox1,Gox2,Gox3,Gox4,Gox5,Gox6,Gox7,Gox8,Gox9,Gox10,Gox11,Gox12,Gox13]
	for i in my_Gox:
		i.set_init_window()
		i.update_config()


	#TWS配置寄存器
	Hox1 = ui_inst(top,'SlidEn&Mode',sldcfg0,31,29,('0(NO)','4(LinNormSld)','5(LinConSld)','6(RioNormSld)','7(RioConSld)'),31,1)
	Hox2 = ui_inst(top,'SlidNum',sldcfg0,26,24,('0(0)','2(2)','3(3)','4(4)','5(5)','6(6)'),31,2)
	Hox3 = ui_inst(top,'SlidBtnEn',sldcfg0,23,23,('0(NO)','1(YES)'),31,3)
	Hox4 = ui_inst(top,'SlidBtnFun',sldcfg0,20,16,[hex(i)[2::]+'('+str(i)+')' for i in range(32)],31,4)
	Hox5 = ui_inst(top,'SlidRes',sldcfg0,15,8,[hex(i)[2::]+'('+str(i)+')' for i in range(256)],31,5)
	Hox6 = ui_inst(top,'NormSlidJdg',sldcfg0,7,6,('0(MoveDistance)','1(PosDistance)','2(SlideOffset)','3(SlideOffset)'),31,6)
	Hox7 = ui_inst(top,'SlideTouchTH',sldcfg0,5,4,('0(ProxTH0)','1(ProxTH1)','2(ProxTH2)','3(ProxTH3)'),33,4)
	Hox8 = ui_inst(top,'ConSldInDeb',sldcfg0,3,0,[hex(i)[2::]+'('+str(i)+')' for i in range(15)],33,1)
	Hox9 = ui_inst(top,'ConSldTimeTH',sldcfg1,31,24,[hex(i)[2::]+'('+str(i)+')' for i in range(256)],33,2)
	Hox10 = ui_inst(top,'ConSldDisTH',sldcfg1,23,16,[hex(i)[2::]+'('+str(i)+')' for i in range(256)],33,3)
	Hox11 = ui_inst(top,'SldSpeedTH',sldcfg1,15,8,[hex(i)[2::]+'('+str(i)+')' for i in range(256)],33,5)
	Hox12 = ui_inst(top,'NormSlideTH',sldcfg1,7,0,[hex(i)[2::]+'('+str(i)+')' for i in range(256)],33,6)
	Hox13 = ui_inst(top,'ClickTimeTH',btncfg,31,24,[hex(i)[2::]+'('+str(i)+')' for i in range(256)],31,7)
	Hox14 = ui_inst(top,'IntervalTH',btncfg,23,16,[hex(i)[2::]+'('+str(i)+')' for i in range(256)],31,8)
	Hox15 = ui_inst(top,'LongPressTH',btncfg,15,8,[hex(i)[2::]+'('+str(i)+')' for i in range(256)],33,7)
	Hox16 = ui_inst(top,'SuperPressTH',btncfg,7,0,[hex(i)[2::]+'('+str(i)+')' for i in range(256)],33,8)
	my_Hox = [Hox1,Hox2,Hox3,Hox4,Hox5,Hox6,Hox7,Hox8,Hox9,Hox10,Hox11,Hox12,Hox13,Hox14,Hox15,Hox16]
	for i in my_Hox:
		i.set_init_window()
		i.update_config()

	#功能菜单
	topmenu = tk.Menu(top)
	menu1 = tk.Menu(topmenu, tearoff=0)
	menu1.add_command(label=u"Config All Regs", command=config_reg)
	menu1.add_command(label=u"Read All Regs", command=read_reg)
	menu1.add_command(label=u"Update UI Default", command=update_reg)
	topmenu.add_cascade(label=u"配置", menu=menu1)
	menu2 = tk.Menu(topmenu, tearoff=0)
	menu2.add_command(label=u"Active", command=active)
	menu2.add_command(label=u"Sleep", command=sleep)
	menu2.add_command(label=u"Correct", command=correct)
	topmenu.add_cascade(label=u"模式", menu=menu2)
	menu3 = tk.Menu(topmenu, tearoff=0)
	menu3.add_command(label=u"采集数据&实时保存", command=save_data)
	menu3.add_command(label=u"采集数据&实时显示", command=dplot_raw)
	#menu3.add_command(label=u"PlotValid", command=dplot_valid)
	#menu3.add_command(label=u"PlotBase", command=dplot_base)
	#menu3.add_command(label=u"PlotDiff", command=dplot_diff)
	topmenu.add_cascade(label=u"功能", menu=menu3)
	menu4 = tk.Menu(topmenu, tearoff=0)
	menu4.add_command(label=u"PlotRaw", command=splot_raw)
	menu4.add_command(label=u"PlotValid", command=splot_valid)
	menu4.add_command(label=u"PlotBase", command=splot_base)
	menu4.add_command(label=u"PlotDiff", command=splot_diff)
	menu4.add_command(label=u"PlotPosition", command=splot_position)
	topmenu.add_cascade(label=u"绘图", menu=menu4)
	top.config(menu=topmenu)


	#进入主循环，等待事件发生
	top.mainloop() 



if __name__ == '__main__':
    main()
