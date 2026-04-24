#!/usr/bin/env python
# coding: utf-8

# In[4]:


from tkinter import filedialog # 開啟檔案對話框
import xlrd
import tkinter as tk
from tkinter import ttk
import pandas as pd 
# 選擇文件(打開excel檔)
def openfile(): 
    sfname = filedialog.askopenfilename(title='選擇Excel文件', filetypes=[('Excel', '*.xlsx'), ('All Files', '*')])    
    return sfname 

# 輸入文件名，回傳第1個工作表數據給data
def readdata(sfname):     
    try:
        T1=En.get() # 讀取輸入的第1個:電纜規格
        T2=En2.get() # 讀取輸入的第2個:電壓等級(V)
        T3=En3.get() # 讀取輸入的第3個:芯數
        T4=En4.get() # 讀取輸入的第4個:線徑  
        T_Len=En5.get() # 讀取輸入的第5個:長度 
        TA=[T1,T2,T3,T4] # 整合所有輸入的分類欄位(電纜規格,電壓等級(V),芯數,線徑)
        TA = list(filter(None,TA)) # 利用filter()去除list的空值   
        # 讀取第1個工作表資料(cable sch)，且以第2列(row)當表頭    
        df = pd.read_excel(sfname,sheet_name = 0,header = [1])  
        df=df.fillna('--') # 空白儲存格用'--'取代
        # 1.材料表:以TA='Type','Core','Size(mm2)'進行分組，並顯示每組相同規格的米數總和T_Len
        df_1=df.groupby(TA).agg({T_Len: sum})
        df_1 = df_1.rename(columns={T_Len: '總米數'}) # 將欄位名稱T_Len('Len.(M)')改為'總米數'
        # 2.領料長度:TB=群組分類(含長度T_Len)後再計算各電纜長度(米)有幾條    
        TB = TA + [T_Len]  # 新增長度分類  
        df_2 = df.groupby(TB,sort = True) # 分類並排序
        df_2 = df_2[T_Len].agg(['count'])  # 計算相同長度的數量
        # 將欄位名稱'count'改為'數量'  
        df_2 = df_2.rename(columns={'count': '數量'})     
        # 另存的檔案位置和名稱
        writer = pd.ExcelWriter('D:/材料表.xlsx') 
        # 1.另存至'材料表'工作表
        df_1.to_excel(writer,sheet_name = "材料表", index = True)
        # 2.另存至'電纜長度'工作表
        df_2.to_excel(writer,sheet_name = "電纜長度",  index = True)
        writer.close()          
        TE = 0
    except KeyError:  
        TE = 1              
    return TE

# 重新載入材料表並傳至step7顯示在UI介面上
def readlen(): 
    book = xlrd.open_workbook('D:/材料表.xlsx') # 載入材料表    
    sheet1 = book.sheets()[1] # 打開第2個工作表
    nrows = sheet1.nrows # 工作表有幾列(rows)       
    ncols = sheet1.ncols # 工作表有幾欄(cols)   
    values = [] # 讀取工作表內的資料並放至values
    for i in range(nrows): 
        row_values = sheet1.row_values(i) # 讀取工作表每一列(row)的資料
        values.append(row_values) # 將每一列(row)資料垂直合併
    return values # 回傳合併後的工作表資料

# 定義樹狀圖表格函數:frame:視窗 、data：工作表資料
def showdata(frame,data):          
    nrows = len(data)    # 工作表有幾列(rows)
    ncols = len(data[0]) # 工作表有幾欄(cols)
    columns = [""] # 建立第1個為空的字串
    for i in range(ncols): 
        columns.append(str(i)) # 建立有幾欄的數字串(第1個為空字串)    
    heading = columns # ['', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9']    
    
    tree = ttk.Treeview(frame, columns=columns, show="headings") 
    # 定義個欄位寬度及對齊方式 
    for item in columns: 
        tree.column(item, width=50, anchor="center") 
    tree.heading(heading[0], text=heading[0]) # 第一列表頭為空     
    # 定義表頭
    for i in range(1, len(columns)): 
        tree.heading(heading[i], text=str(i)) 
    # 取出表格內容 
    i = 0 
    for v in data: # 逐一取出每列內容並合併
        v.insert(0, i + 1) #取出第一列內容(序號)         
        tree.insert('', i, values=(v)) 
        i += 1     
    return tree

def hide_ERR(): # 隱藏"分類名稱錯誤"訊息
    label8.grid_forget()

def show_ERR(): # 顯示"分類名稱錯誤"訊息
    label8.grid(row=5,column=0)

# 打開文件並以樹狀表格形式顯示
def openshow(): 
    global root     
    p=En.get()
    filename=openfile() 
    TE = readdata(filename) 
    if TE == 0: 
        hide_ERR()
        data=readlen() 
        tree=showdata(root,data) 
        tree.place(relx=0.03,rely=0.2,relheight=0.7,relwidth=0.9) # 在指定位置顯示視窗和資料
    else:
        show_ERR()
        
# 建立視窗(含人機介面UI)
root = tk.Tk() # 建立主視窗 root
root.title("材料表")  # 設定視窗標題
root.geometry("750x400") # 設定視窗大小    
# 建立 Button 按鈕，按下按鈕會呼叫step 3執行'openshow'函式
B1 = tk.Button(root, text="打開excel", command=openshow) 
B1.grid(padx='10',row=1,column=12) # 加入於第1行第1欄
label =tk.Label(root, text="輸入分類名稱",bg="#7AFEC6",fg='blue',font=("標楷體",14,"bold"))
label.grid(padx='5',row=1,column=0) # 加入於第1行第2欄
# 1.第1組輸入框:電纜規格
label1 =tk.Label(root, text="電纜規格",fg='blue',font=("標楷體",12,"bold"))
label1.grid(padx='10',row=0,column=1) # 加入於第1行第2欄
text1 = tk.StringVar() # 輸入第1個分類名稱變數
text1.set("TYPE") # 預設文字為"TYPE"
En=tk.Entry(root,width=10, textvariable=text1) # 建立第1個電纜規格單行輸入框
En.grid(padx='10',row=1,column=1) # 加入於第2行第2欄
# 2.第2組輸入框:電壓等級(V)
label2 =tk.Label(root, text="電壓等級",fg='blue',font=("標楷體",12,"bold"))
label2.grid(padx='10',row=0,column=2) # 加入於第1行第3欄
text2 = tk.StringVar() # 輸入第2個分類名稱變數
text2.set("RATE(V)") # 預設文字為"RATE(V)"
En2=tk.Entry(root,width=10, textvariable=text2) # 建立第2個芯數單行輸入框
En2.grid(padx='10',row=1,column=2) # 加入於第2行第3欄
# 3.第3組輸入框:芯數
label3 =tk.Label(root, text="芯數",fg='blue',font=("標楷體",12,"bold"))
label3.grid(padx='10',row=0,column=3) # 加入於第1行第4欄
text3 = tk.StringVar() # 輸入第2個分類名稱變數
text3.set("CORENO.") # 預設文字為"CORENO."
En3=tk.Entry(root,width=10, textvariable=text3) # 建立第2個芯數單行輸入框
En3.grid(padx='10',row=1,column=3) # 加入於第2行第4欄
# 4.第4組輸入框:線徑
label4 =tk.Label(root, text="線徑",fg='blue',font=("標楷體",12,"bold"))
label4.grid(padx='10',row=0,column=4) # 加入於第1行第5欄
text4 = tk.StringVar() # 輸入第3個分類名稱變數
text4.set("SIZE(mm2)") # 預設文字為"SIZE(mm2)"
En4=tk.Entry(root,width=10, textvariable=text4) # 建立第3個線徑單行輸入框
En4.grid(padx='10',row=1,column=4) # 加入於第2行第5欄
# 5.第5組輸入框:長度
label5 =tk.Label(root, text="長度",fg='blue',font=("標楷體",12,"bold"))
label5.grid(padx='10',row=0,column=5) # 加入於第1行第6欄
text5 = tk.StringVar() # 輸入第3個分類名稱變數
text5.set("LEN.(M)") # 預設文字為"LEN.(M)"
En5=tk.Entry(root,width=10, textvariable=text5) # 建立第3個線徑單行輸入框
En5.grid(padx='10',row=1,column=5) # 加入於第2行第6欄
label8 =tk.Label(root, text="分類名稱錯誤",bg="#7AFEC6",fg='red',font=("標楷體",14,"bold"))
root.mainloop()


# In[ ]:




