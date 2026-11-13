# U4ACT02 - RESTCONF con Python y Tkinter

**Alumno:** José Fernando Alfaro Almanza

## Descripción de la práctica

En esta práctica desarrollé una aplicación gráfica utilizando Python y Tkinter para administrar interfaces de un router Cisco Catalyst 8000v mediante RESTCONF.

La aplicación permite consultar, crear, actualizar y eliminar interfaces utilizando los métodos HTTP GET, POST, PUT y DELETE.

También incluye mensajes de confirmación, indicadores visuales y manejo de errores.

## Preguntas de reflexión

**1. ¿Cómo se convierten los datos capturados en Tkinter al diccionario yangConfig?**

Los datos se obtienen de los campos de texto mediante `.get()`. Después se organizan dentro de un diccionario llamado `yangConfig`, que contiene la información necesaria para configurar una interfaz. Finalmente, los datos se envían al router mediante RESTCONF.

**2. ¿Qué ventajas tienen los eventos y callbacks de Tkinter frente a los scripts lineales?**

Permiten ejecutar diferentes funciones mediante botones, sin necesidad de iniciar un programa distinto para cada operación. Esto hace que la aplicación sea más sencilla, interactiva y fácil de utilizar.

**3. ¿Qué cambios se realizaron para eliminar la interfaz Loopback99?**

Se utilizó el método DELETE en lugar de PUT, indicando la dirección RESTCONF de Loopback99. También se agregó una ventana de confirmación antes de eliminarla y un mensaje para mostrar el resultado de la operación.

## Resultados obtenidos

Se comprobó el funcionamiento de los cuatro métodos RESTCONF:

- GET: consulta de interfaces.
- POST: creación de Loopback99.
- PUT: actualización de la configuración.
- DELETE: eliminación de Loopback99.

También se verificó el manejo de errores HTTP 401 y 404.

## Conclusión

Esta práctica me permitió aprender a utilizar Python y RESTCONF para administrar interfaces de un router Cisco desde una aplicación gráfica. Comprendí cómo automatizar configuraciones y facilitar tareas de administración de redes.
