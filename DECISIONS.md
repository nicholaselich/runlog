1. From and To query parameters: `from` date is inclusive and `to` date is exclusive. Dates are interpreted at midnight in the database session's timezone 
2. Pagination: offset
3. Strava Activity ID is nullable and cannot be changed after creation. 
4. POST/PATCH input AwareDatetime and 422 for naive timestamps
5. POST: 201
6. DUPLICATE: 409
7. DELETE: 204
8. DELETE (already deleted): 404
9. PATCH uses `exclude_unset`, so null clears a field and omitting one leaves it alone
10. Elapsed Time > Moving Time checked in PATCH
11. Postgres starts weeks on Mondays, so stat endpoints start the week on Monday
12. Weeks with zero runs get returned with zeros for easier charting/visualizations
