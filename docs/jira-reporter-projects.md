# US: Sync Jira Projects (Reporter)

## Overview
This feature implements automatic synchronization of Jira projects where the current user is a reporter of Epic, Story, or Étude issues.

## Features Implemented

### 1. Auto-Sync on Login
- Projects are automatically synchronized when the user logs in via OAuth
- Runs in the background without blocking the login flow
- Failures in sync do not prevent successful login

### 2. Manual Refresh
- `POST /jira/projects/sync` endpoint triggers a manual refresh
- Clears temporarily hidden projects on manual refresh
- Updates session cache with latest project data

### 3. Project Filtering
- **Status filtering**: Excludes issues with status in (Annulé, Done, Cancelled, Terminé)
- **Issue type filtering**: Only includes Epic, Story, and Étude issue types
- **Reporter filtering**: Only shows projects where user is the reporter (via JQL: `reporter = currentUser()`)
- **Instance filtering**: Only syncs from active/connected Jira instances

### 4. Project Aggregation
- Projects are aggregated by `projectKey` across all issues
- Tracks issue count per project
- Records last updated timestamp
- Supports multiple Jira instances

### 5. Project Hiding/Masking
- **Temporary hiding**: Hidden until next manual refresh
- **Permanent hiding**: Survives manual refresh
- `POST /jira/projects/{projectKey}/hide?permanent=true|false`
- `POST /jira/projects/{projectKey}/unhide`

### 6. Inactive Project Detection
- Projects with no active issues (all Done/Annulé) are not listed
- `isActive` flag tracks project activity status

## API Endpoints

### GET /jira/projects/reporter
Returns the list of projects where the user is a reporter.

**Response:**
```json
{
  "projects": [
    {
      "projectKey": "PROJ",
      "projectName": "Project Name",
      "cloudId": "cloud-id-123",
      "issueCount": 5,
      "lastUpdated": "2024-01-15T10:00:00.000Z",
      "visibility": "visible",
      "isActive": true
    }
  ],
  "total": 1,
  "lastSyncAt": "2024-01-15T10:00:00.000Z"
}
```

### POST /jira/projects/sync
Manually trigger a sync of reporter's projects.

### POST /jira/projects/{projectKey}/hide
Hide a project from the list.

**Query Parameters:**
- `permanent` (boolean): If true, hide permanently; if false (default), hide temporarily

### POST /jira/projects/{projectKey}/unhide
Unhide a previously hidden project and trigger a sync to restore it.

## Data Models

### ProjectVisibility Enum
- `VISIBLE`: Project is visible in the list
- `HIDDEN_TEMPORARY`: Hidden until next manual refresh
- `HIDDEN_PERMANENT`: Hidden permanently until explicitly unhidden

### JiraProjectOut
- `projectKey`: Unique project identifier
- `projectName`: Human-readable project name
- `cloudId`: Jira instance identifier
- `issueCount`: Number of active issues where user is reporter
- `lastUpdated`: Timestamp of most recently updated issue
- `visibility`: Current visibility state
- `isActive`: Whether project has active issues

## Session Storage
Projects data is stored in Redis session:
- `reporter_projects`: List of visible projects (serialized)
- `reporter_projects_sync_at`: Last sync timestamp
- `hidden_projects`: Map of projectKey -> visibility state

## Implementation Details

### JQL Query
```jql
reporter = currentUser() 
AND type in (Epic, Story, "Étude") 
AND status NOT IN (Annulé, Done, Cancelled, Terminé)
```

### Pagination
- Fetches up to 50 results per instance
- Simplified pagination for performance
- Can be extended for full pagination if needed

### Error Handling
- Client errors for individual instances don't fail entire sync
- Login succeeds even if project sync fails
- Proper HTTP status codes (401, 502, etc.)

## Testing
- 205 tests total, 100% code coverage
- 16 dedicated tests for project sync service
- 11 tests for API endpoints
- Integration tests for login auto-sync
- Edge case handling (pagination, errors, missing data)

## Acceptance Criteria Compliance

✅ **1. Refresh login**: Auto-sync triggered on OAuth callback  
✅ **2. Status filtering**: Annulé/Done excluded via JQL  
✅ **3. Instance filtering**: Only active instances included  
✅ **4. Permanent hiding**: Projects stay hidden until manual unhide  
✅ **5. Inactive projects**: Projects with no active issues are not listed  

## Future Enhancements
- Full pagination support for projects with >50 active issues
- Background scheduled sync (e.g., every hour)
- Project favorites/pinning
- Bulk hide/unhide operations
- Export projects list
