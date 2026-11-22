#!/usr/bin/env python3
"""OM AI PC Companion — local, read-only Windows desktop app (Tkinter).

Shows machine health, suggestions and task receipts. This is NOT remote control.
Only intended to run on the store PC under an authorized account.
"""
import json
import os
import threading
import tkinter as tk
from pathlib import Path
from tkinter import ttk, messagebox
import webbrowser
import agent

ROOT=Path(__file__).resolve().parent
CONFIG=ROOT/'config.local.json'

class App:
    def __init__(self,top):
        self.top=top
        top.title('OM AI · PC Intelligence')
        top.geometry('1040x720')
        top.minsize(760,520)
        top.configure(bg='#111b30')
        self.style=ttk.Style()
        self.style.theme_use('clam')
        self.style.configure('TFrame',background='#f5f7fb')
        self.style.configure('TLabel',background='#f5f7fb',foreground='#223148',font=('Segoe UI',10))
        self.style.configure('TNotebook',background='#f5f7fb')
        self.style.configure('TNotebook.Tab',font=('Segoe UI',10),padding=(18,10))
        self.style.configure('Treeview',font=('Segoe UI',9),rowheight=28)
        self.title=tk.Label(top,text='OM AI   /   PC INTELLIGENCE',bg='#111b30',fg='#eff2ff',font=('Segoe UI',20,'bold'),anchor='w',padx=25,pady=18)
        self.title.pack(fill='x')
        bar=ttk.Frame(top,padding=12);bar.pack(fill='x')
        self.info=ttk.Label(bar,text='Local monitoring only. No software will be stopped or restarted.')
        self.info.pack(side='left')
        ttk.Button(bar,text='Refresh metrics',command=self.refresh).pack(side='right',padx=5)
        ttk.Button(bar,text='Private website',command=self.open_site).pack(side='right',padx=5)
        self.book=ttk.Notebook(top);self.book.pack(fill='both',expand=True,padx=16,pady=(0,12))
        health=ttk.Frame(self.book,padding=17);self.book.add(health,text='PC health')
        jobs=ttk.Frame(self.book,padding=17);self.book.add(jobs,text='Automation tasks')
        rules=ttk.Frame(self.book,padding=17);self.book.add(rules,text='Safety & recommendations')
        self.labels={}
        for i,(title,key) in enumerate([('CPU load','cpu_pct'),('RAM use','ram_pct'),('RAM available','ram_available_gb'),('Disk free','disk_free_gb'),('CPU temperature','cpu_temp_c'),('GPU temperature','gpu_temp_c'),('GPU utilization','gpu_pct'),('Telemetry','status')]):
            panel=ttk.LabelFrame(health,text=title,padding=(15,13))
            panel.grid(row=i//4,column=i%4,sticky='nsew',padx=6,pady=6)
            label=ttk.Label(panel,text='—',font=('Segoe UI',15,'bold'));label.pack()
            self.labels[key]=label
        for i in range(4):health.grid_columnconfigure(i,weight=1)
        self.procs=ttk.Treeview(health,columns=('count','ram','cpu','protected'),show='headings',height=11)
        for column,w in [('count',80),('ram',100),('cpu',100),('protected',120)]:self.procs.heading(column,text=column.title());self.procs.column(column,width=w,anchor='center')
        self.procs['columns']=('name','count','ram','cpu','protected')
        for name,w in [('name',260),('count',80),('ram',100),('cpu',100),('protected',120)]:self.procs.heading(name,text=name.title());self.procs.column(name,width=w)
        self.procs.grid(row=2,column=0,columnspan=4,sticky='nsew',pady=14)
        health.grid_rowconfigure(2,weight=1)
        self.jobs=ttk.Treeview(jobs,columns=('job','provider','state','last','action'),show='headings')
        for col,width in [('job',280),('provider',130),('state',140),('last',170),('action',450)]:
            self.jobs.heading(col,text=col.title());self.jobs.column(col,width=width)
        self.jobs.pack(fill='both',expand=True)
        self.notes=tk.Text(rules,bg='#fff',fg='#20314a',wrap='word',font=('Segoe UI',10),relief='flat',padx=15,pady=15)
        self.notes.pack(fill='both',expand=True)
        self.notes.insert('1.0','Read-only by design. No data collected yet.\n');self.notes.configure(state='disabled')
        self.refresh()
    def open_site(self):
        link=os.environ.get('OM_AI_PRIVATE_DASHBOARD_URL','')
        if not link.startswith('https://script.google.com/'):
            messagebox.showinfo('OM AI','Private website URL is not configured on this PC. Sign-in remains required.')
            return
        webbrowser.open(link)
    def refresh(self):
        self.info.config(text='Reading local metrics and job receipts…')
        def work():
            cfg=agent.read_json(CONFIG,agent.read_json(ROOT/'config.example.json',{}))
            receipts=agent.read_json(ROOT/'data'/'job-receipts.json',[])
            snap=agent.build_snapshot(cfg,receipts if isinstance(receipts,list) else [])
            self.top.after(0,lambda:self.show(snap))
        threading.Thread(target=work,daemon=True).start()
    def show(self,snap):
        pc=snap.get('pc',{})
        for key,el in self.labels.items():
            val=pc.get(key)
            unit=('%' if key in ('cpu_pct','ram_pct','gpu_pct') else ' °C' if '_temp_' in key else ' GB' if key in ('ram_available_gb','disk_free_gb') else '')
            el.config(text='Not measured' if val is None else str(val)+unit)
        for row in self.procs.get_children():self.procs.delete(row)
        for p in pc.get('processes',[]):
            self.procs.insert('', 'end',values=(p['name'],p['count'],p['ram_mb'],p['cpu_pct'],'Protected' if p['protected'] else 'Review only'))
        for row in self.jobs.get_children():self.jobs.delete(row)
        for j in snap.get('jobs',[]):
            self.jobs.insert('', 'end',values=(j['name'],j['provider'],j['state'],j['last_run'] or 'Never',j['next_action']))
        lines=['OM AI PC — read-only optimization suggestions','',
               'The PC application never ends tasks, restarts services or changes device settings.','']
        for a in snap.get('alerts',[]):lines.append(f"[{a['severity'].upper()}] {a['title']}\n{a['detail']}\nAction: {a['recommendation']}\n")
        if snap['pc']['status']!='measured':lines.append('PC metrics unavailable. Verify psutil installation and disk path.')
        self.notes.configure(state='normal');self.notes.delete('1.0','end');self.notes.insert('1.0','\n'.join(lines));self.notes.configure(state='disabled')
        self.info.config(text='Last local check: '+snap['sent_at']+' · no process changes')

if __name__=='__main__':
    app=tk.Tk()
    App(app)
    app.mainloop()
