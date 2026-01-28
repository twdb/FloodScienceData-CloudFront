

# Git Use Case Guide
# USE CASE 1 — Clone the Repository to Your Local Machine

Goal: Download the code from GitHub to your computer.

Steps:

1.  git clone <https://github.com/twdb/FloodScienceData-CloudFront.git>
2.  cd FloodScienceData-CloudFront

# USE CASE 2 — Create a New Branch Before Making Changes

Goal: Create a dedicated branch for the work you will do.

Steps:

1.  git switch -c feature/your-branch-name

Examples:  
feature/add-logging  
fix/timestamp-issue  
restructure/new-folder-layout

Note: Never commit directly to main.

# USE CASE 3 — Check Which Branch You Are Working On

Goal: Confirm your current branch before committing or pushing.

Steps:

1.  git branch
2.  or run: git status

The branch with \* is your current branch.



# USE CASE 4 — View Changes You Made Locally

Goal: See modified, added, or deleted files.

Steps:

1.  git status


# USE CASE 5 — Stage Your Changes

Goal: Tell Git which changes to include in the next commit.

Steps:  
Add all changes:  
git add -A

Add one specific file:  
git add path/to/file



# USE CASE 6 — Commit Your Changes With a Message

Goal: Save your staged changes with a description.

Steps:  
git commit -m "Describe what you changed"

Examples:  
git commit -m "Add CONTRIBUTING.md"  
git commit -m "Fix timestamp formatting issue"  
git commit -m "Improve folder structure"


# USE CASE 7 — Push Your Branch to GitHub

Goal: Upload your work to the remote repository.

Steps:  
First push for a new branch:  
git push -u origin feature/your-branch-name

After the first time:  
git push



# USE CASE 8 — Add a New File (Example: CONTRIBUTING.md) and Push It

Goal: Add new files to Git and upload them.

Steps:

1.  git add file-name
2.  git commit -m "Add file-name"
3.  git push

# USE CASE 9 — Open a Pull Request (PR)

Goal: Request to merge your work into main.

Steps:

1.  Go to <https://github.com/twdb/FloodScienceData-CloudFront>
2.  Click "Compare & Pull Request"
3.  Choose:  
    From: your branch  
    Into: main
4.  Add a description
5.  Submit the PR

***

# USE CASE 10 — Update Your Branch With Latest main Changes

Goal: Keep your work updated with new commits from main.

Steps:

1.  git switch main
2.  git pull
3.  git switch feature/your-branch-name
4.  git pull --rebase origin main

***

# USE CASE 11 — View All Local and Remote Branches

Goal: See which branches exist.

Steps:  
git branch -a



# USE CASE 12 — Switch to Another Branch

Goal: Move between branches safely.

Steps:  
git switch branch-name

Example:  
git switch restructure/new-layout



# USE CASE 13 — Delete a Local Branch After Merging

Goal: Clean up local branches you no longer need.

Steps:  
git branch -d branch-name


# End-to-End Workflow Summary

1.  git clone <https://github.com/twdb/FloodScienceData-CloudFront.git>
2.  cd FloodScienceData-CloudFront
3.  git switch -c feature/my-work
4.  (make changes)
5.  git add -A
6.  git commit -m "My update"
7.  git push -u origin feature/my-work
8.  Open Pull Request and merge into main


