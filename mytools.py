#!/usr/bin/python
# find icons at /usr/share/icons
# pyinstaller -F mytools.py 打包
import os
from gi.repository import Gtk as gtk, AppIndicator3 as appindicator
from gi.repository import Notify as notify
   

def main():
  notify.init("MyTools")
  indicator = appindicator.Indicator.new("MyTools", "applications-microblogging-panel", appindicator.IndicatorCategory.APPLICATION_STATUS)
  indicator.set_status(appindicator.IndicatorStatus.ACTIVE)
  indicator.set_menu(menu())
  gtk.main()

def menu():
  menu = gtk.Menu()

  command_grep_tool = gtk.MenuItem('Grep Tool')
  command_grep_tool.connect('activate', start_grep_tool)
  menu.append(command_grep_tool)

  exittray = gtk.MenuItem('Exit')
  exittray.connect('activate', quit)
  menu.append(exittray)
  
  menu.show_all()
  return menu

def getOutput(cmd):
  r = os.popen(cmd)
  text = r.read()
  r.close()
  return text
  
def start_grep_tool(_):
  os.system("ps -ef | grep \"python3 -u ./grep_tool/grep_tool.py\" | grep -v \"color\" | awk \'{print $2}\' | xargs kill")
  os.system("cd /home/jiaying/Documents/misc && nohup python3 -u ./grep_tool/grep_tool.py &")

def quit(_):
  os.system("ps -ef | grep \"python3 -u ./grep_tool/grep_tool.py\" | grep -v \"color\" | awk \'{print $2}\' | xargs kill")
  gtk.main_quit()
  

if __name__ == "__main__":
  main()
