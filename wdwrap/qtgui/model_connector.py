#  Copyright (c) 2020. Mikolaj Kaluszynski et. al. CAMK, AkondLab
from abc import abstractmethod
from threading import Lock
from typing import Optional, Callable

from PySide2.QtCore import QObject
from traitlets import HasTraits


class ModelConnector:
    """Abstract base for model connectors - connects controls widget to some implementation of the model

    This class implements View part for Qt controls widgets, the model part have to be implemented in
    subclass.
    """

    def __init__(self) -> None:
        super().__init__()
        self.view_slot = None
        self.view_signal = None
        self.disabling_semaphore = Lock()
        self._view_singal_handler = lambda value: self._on_view_signal(value)

    @abstractmethod
    def set_model_value(self, value):
        """To be implemented in subclass"""
        pass

    def set_view_value(self, value):
        """To be called from subclass"""
        if self.disabling_semaphore.acquire(blocking=False):
            try:
                self.view_slot(value)
            finally:
                self.disabling_semaphore.release()

    def connect_view(self, slot, signal):
        if self.view_signal is not None:
            self.view_signal.disconnect(self._view_singal_handler)
        self.view_signal = signal
        self.view_slot = slot
        if self.view_signal is not None:
            self.view_signal.connect(self._view_singal_handler)

    def disconnect(self):
        if self.view_signal is not None:
            self.view_signal.disconnect(self._view_singal_handler)

    def _on_view_signal(self, value):
        if self.disabling_semaphore.acquire(blocking=False):
            try:
                self.set_model_value(value)
            finally:
                self.disabling_semaphore.release()

class QObjectModelConnector(ModelConnector):
    """Model connectors - connects controls widget to some QObject"""
    def __init__(self) -> None:
        super().__init__()
        self.model_object: Optional[QObject] = None
        self.model_slot = None
        self.model_signal = None

    def connect_model(self, model_object: QObject, model_slot, model_signal, value=None):
        try:
            self.model_signal.disconnect(self._on_model_changed_signal)
        except (AttributeError, RuntimeError):
            pass
        self.model_object = model_object
        self.model_slot = model_slot
        self.model_signal = model_signal
        self.model_signal.connect(self._on_model_changed_signal)
        try:
            self.set_view_value(value)
        except AttributeError:
            pass

    def disconnect(self):
        super().disconnect()
        if self.model_signal is not None:
            self.model_signal.disconnect(self._on_model_changed_signal)

    def set_model_value(self, value):
        try:
            self.model_slot(value)
        except AttributeError:
            pass

    def _on_model_changed_signal(self, value):
        self.set_view_value(value)

class PythonPropertyConnector(ModelConnector):
    """Model connectors - connects controls widget to ordinary python object's property, no model value observing"""
    def __init__(self, property_name: Optional[str] = None) -> None:
        super().__init__()
        self.model_object: Optional[HasTraits] = None
        self.model_property: Optional[str] = property_name

    def connect_model(self, model_object: HasTraits, property_name: Optional[str] = None):
        self.model_object = model_object
        if property_name is not None:
            self.model_property = property_name
        try:
            self.set_view_value(getattr(self.model_object, self.model_property))
        except AttributeError:
            pass

    def set_model_value(self, value):
        try:
            setattr(self.model_object, self.model_property, value)
        except AttributeError:
            pass

class PythonMethodConnector(ModelConnector):
    """Model connectors - connects controls widget to ordinary python object's method (getter),
    R/O and no model observing"""
    def __init__(self, method_name: Optional[str] = None, **method_kwargs) -> None:
        super().__init__()
        self.model_object: Optional[HasTraits] = None
        self.model_method: Optional[str] = method_name
        self.model_method_kwargs = method_kwargs

    def connect_model(self, model_object: HasTraits, method_name: Optional[str] = None, **method_kwargs):
        self.model_object = model_object
        if method_name is not None:
            self.model_method = method_name
            self.model_method_kwargs = method_kwargs
        try:
            self.set_view_value(getattr(self.model_object, self.model_method)(**self.model_method_kwargs))
        except AttributeError:
            pass

    def set_model_value(self, value):
        raise TypeError('PythonMethodConnector is read only, `set_model_value` not allowed')

class TraitletsModelConnector(ModelConnector):
    """Model connectors - connects controls widget to some `traitlets` object"""
    def __init__(self, property_name: Optional[str] = None) -> None:
        super().__init__()
        self._handler = lambda change: self._on_model_value_changed(change)
        self.model_object: Optional[HasTraits] = None
        self.model_property: Optional[str] = property_name

    def connect_model(self, model_object: HasTraits, property_name: Optional[str] = None):
        if self.model_object is not None:
            self.model_object.unobserve(self._handler)
        self.model_object = model_object
        if property_name is not None:
            self.model_property = property_name
        self.model_object.observe(self._handler, [self.model_property])
        try:
            self.set_view_value(getattr(self.model_object, self.model_property))
        except AttributeError:
            pass

    def disconnect(self):
        super().disconnect()
        if self.model_object is not None:
            self.model_object.unobserve(self._handler)

    def set_model_value(self, value):
        try:
            setattr(self.model_object, self.model_property, value)
        except AttributeError:
            pass

    def _on_model_value_changed(self, change):
        self.set_view_value(change.new)


class HasModelConnector:
    """Base class for widgets implementing connectiong to the model via `ModelConnector` derived classes"""

    def __init__(self) -> None:
        super().__init__()
        self.view_signal = None
        self.view_slot = None
        self._model_connector = None
        # if model_connector is None:
        model_connector = ModelConnector()
        self.model_connector = model_connector

    @property
    def model_connector(self) -> ModelConnector:
        return self._model_connector

    @model_connector.setter
    def model_connector(self, model_connector: ModelConnector):
        if self.model_connector is not None:
            self.model_connector.disconnect()
        self._model_connector = model_connector
        slot, signal = self.get_slot_and_signal_for_view()
        self.model_connector.connect_view(slot, signal)

    def get_slot_and_signal_for_view(self):
        return self.view_slot, self.view_signal

def connected_widget(widget_class, connector_object, view_slot: str, view_signal: str, **kwargs):
    """Factory function creating objects of class being subclass of `widget_class` and `HasModelConnector`"""
    def _constructor(self):
        widget_class.__init__(self)
        HasModelConnector.__init__(self)

    subclass = type('ConnectedWidget',
                    (widget_class, HasModelConnector),
                    {
                        '__init__': _constructor
                    }
                    )
    instance: HasModelConnector = subclass(**kwargs)
    instance.view_slot = getattr(instance, view_slot)
    if view_signal is not None:
        instance.view_signal = getattr(instance, view_signal)
    else:
        try:
            instance.setReadOnly(True)  # Try to make control read-only if no editing signal provided
        except AttributeError:
            pass
    if connector_object is not None:
        instance.model_connector = connector_object
    return instance