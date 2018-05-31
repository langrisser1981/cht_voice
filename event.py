from threading import Thread
import queue


class EventManager():
    def __init__(self):
        self.__eventQueue = queue.Queue()
        self.__handlers = {}
        self.__active = False
        self.__thread = Thread(target = self.__run)
        
        
    def __run(self):
        while self.__active == True:
            try:
                event = self.__eventQueue.get(block=True, timeout=1)
                self.__eventProcess(event)
                
            except queue.Empty:
                pass
            
            
    def __eventProcess(self, event):
        if event.name in self.__handlers:
            for handler in self.__handlers[event.name]:
                handler(event)
                
                
    def start(self):
        self.__active = True
        self.__thread.start()
        
        
    def stop(self):
        self.__active = False
        self.__thread.join()
        
        
    def addEventListaner(self, eventName, handler):
        try:
            handlerList = self.__handlers[eventName]
        except KeyError:
            handlerList = []
            
        self.__handlers[eventName] = handlerList
        if handler not in handlerList:
            handlerList.append(handler)
            
            
    def removeEventListaner(self, eventName, handler):
        try:
            handlerList = self.__handlers[eventName]
        except KeyError:
            return
        
        self.__handlers[eventName] = handlerList
        if handler in handlerList:
            handlerList.remove(handler)
            
            
    def dispatchEvent(self, event):
        self.__eventQueue.put(event)
        
        
class Event():
    def __init__(self, name=None):
        self.name = name
        self.data = {}
        
