
Sync module
===========

This module is the heart of Maestral, it contains the classes for sync functionality.

The :class:`SyncEngine` provides access to the current sync state through its properties
and provides the methods which are necessary to complete an upload or a download sync
cycle. This includes methods to wait for and return local and remote changes, to sort
those changes and discard any excluded items and to apply local changes to the Dropbox
server and vice versa.

The :class:`SyncMonitor` actually coordinates the sync process with its threads for
startup, download-sync, upload-sync and periodic maintenance.

Notes on event processing:

Remote events come in three types: DeletedMetadata, FolderMetadata and FileMetadata.
The Dropbox API does not differentiate between created, moved or modified events.
Maestral processes remote events as follows:

  1) :meth:`SyncEngine.wait_for_remote_changes` blocks until remote changes are available.
  2) :meth:`SyncEngine.get_remote_changes` lists all remote changes since the last sync.
     Events for entries which are excluded by selective sync and hard-coded file names
     which are always excluded (e.g., '.DS_Store') are filtered out at this stage.
     Multiple events per file path are combined to one. This is rarely necessary, Dropbox
     typically already provides only a single event per path but this is not guaranteed
     and may change. One exception is sharing a folder: This is done by removing the
     folder from Dropbox and re-mounting it as a shared folder and produces at least one
     DeletedMetadata and one FolderMetadata event. If querying for changes *during* this
     process, multiple DeletedMetadata events may be returned. If a file / folder event
     implies a type changes, e.g., replacing a folder with a file, we explicitly generate
     the necessary DeletedMetadata here to simplify conflict resolution.
  3) :meth:`SyncEngine.apply_remote_changes`: Sorts all events hierarchically, with
     top-level events coming first. Deleted and folder events are processed in order, file
     events in parallel with up to 6 worker threads. Sync conflicts are detected by
     comparing the file "rev" with our locally saved rev. We assign folders a rev of
     ``'folder'`` and deleted / non-existent items a rev of ``None``. If revs are equal,
     the local item is the same or newer as on Dropbox and no download / deletion occurs.
     If revs are different, we compare content hashes. Folders are assigned a hash of
     'folder'. If hashes are equal, no download occurs. If they are different, we check if
     the local item has been modified since the last download sync. In case of a folder,
     we take the newest change of any of its children. If the local entry has not been
     modified since the last sync, it will be replaced. Otherwise, we create a conflicting
     copy.
  4) :meth:`SyncEngine.notify_user`: Shows a desktop notification for the remote changes.

Local file events come in eight types: For both files and folders we collect created,
moved, modified and deleted events. They are processed as follows:

  1) :meth:`SyncEngine.wait_for_local_changes`: Blocks until local changes are registered
     by :class:`FSEventHandler` and returns those changes. Events ignored by a "mignore"
     pattern as well as hard-coded file names and changes in our cache path are filtered
     out at this stage. Further, event are cleaned up to return the minimum number
     necessary to reproduce the actual changes: Multiple events per path are combined into
     a single event which reproduces the file change. The only exception is when the entry
     type changes from file to folder or vice versa: in this case, both deleted and
     created events are kept. Further, when a whole folder is moved or deleted, we discard
     the moved or deleted events for its children.
  2) :meth:`SyncEngine.apply_local_changes`: Sorts local changes hierarchically and
     applies events in the order of deleted, folders and files. Deletions and creations
     will be carried out in parallel with up to 6 threads. Conflict resolution and the
     actual upload will be handled as follows: For created and moved events, we check if
     the new path has been excluded by the user with selective sync but still exists on
     Dropbox. If yes, it will be renamed by appending "(selective sync conflict)". On
     case-sensitive file systems, we check if the new path differs only in casing from an
     existing path. If yes, it will be renamed by appending "(case conflict)". If a file
     has been replaced with a folder or vice versa, we check if any un-synced changes will
     be lost by replacing the remote item and create a conflicting copy if necessary.
     Dropbox does not handle conflict resolution for us in this case. For created or
     modified files, check if the local content hash equals the remote content hash. If
     yes, we don't upload but update our rev number. If no, we upload the changes and
     specify the rev which we want to replace or delete. If the remote item is newer
     (different rev), Dropbox will handle conflict resolution for us. We finally confirm
     the successful upload and check if Dropbox has renamed the item to a conflicting
     copy. In the latter case, we apply those changes locally.

.. automodule:: sync
   :members:
   :show-inheritance:
