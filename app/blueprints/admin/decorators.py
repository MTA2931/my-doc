"""Reusable access-control decorators for the admin panel.

``role_required`` is part of the public API of the project (see
``app.services.access``) and is re-exported here for convenience::

    from ..admin.decorators import role_required
"""

from ...services.access import capability_required, login_required, role_required

__all__ = ["role_required", "capability_required", "login_required"]
