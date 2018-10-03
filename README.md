ReadProperty
============
Read properties from a BACNet/IP device. This block does not respond to any `whois` nor data-sharing requests, and requires an address for the target device as discovery is not supported. For every signal processed, a new requst is made to the target device and a single value read.

Properties
----------
- **address**: A string of the IP address (optional subnet mask and port number) of target device. For example, `192.168.100.100/24:47808`. Hostnames are not supported, raises `ValueError` if the supplied address cannot be parsed.
- **array_index**: If the value being read is inside an array, optionally specify the index of the desired value.
- **enrich**: Signal Enrichment
  - *exclude_existing*: If checked (true), the attributes of the incoming signal will be excluded from the outgoing signal. If unchecked (false), the attributes of the incoming signal will be included in the outgoing signal.
  - *enrich_field*: (hidden) The attribute on the signal to store the results from this block. If this is empty, the results will be merged onto the incoming signal. This is the default operation. Having this field allows a block to 'save' the results of an operation to a single field on an incoming signal and notify the enriched signal.
- **instance_num**: Which instance of the Object Type to read.
- **my_address**: Address to bind to receive responses from BACNet devices.
- **object_type**: One of the standard BACNet Object Types (for example `analogValue`, note the use of camelCase capitalization without spaces). Vendor-defined custom-objects are not supported. Raises `ValueError` if not a recognized object type.
- **property_id**: One of the defined Properties for this object type. Raises `ValueError` if not a valid property for this type.
- **timeout**: Seconds to wait for a response from a target device before raising an exception.

Inputs
------
- **default**: Any list of Signals, one property is read for each signal.

Outputs
-------
- **default**: The same list of signals, enriched with the attribute defined by `results_field`, containing the result of this request, and key:value pairs in `details` describing the request.

Commands
--------
None

