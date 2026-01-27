

# Contributing to FloodScienceData-CloudFront
Please follow this guide to ensure all contributions are consistent, reviewed, and safely merged into the `main` branch.


## 1. Clone the Repository

Use the following command to pull the repository to your local machine:

git clone <https://github.com/twdb/FloodScienceData-CloudFront.git>

Move into the project folder:

cd FloodScienceData-CloudFront


## 2. Create a New Branch

Always create a new branch before making changes.  
Never commit directly to `main`.

git switch -c feature/your-branch-name

Branch name examples:  
feature/add-logging  
fix/timestamp-bug  
restructure/new-folder-layout



## 3. Make Your Changes Locally

Modify or add files using your preferred editor (VS Code, PyCharm, etc.).

Check your changes anytime:

git status

***

## 4. Stage Your Changes

Add all updated files: git add -A

Or add a specific file:

git add path/to/file



## 5. Commit Your Changes

Write a clear message about what you updated:

git commit -m "Describe what you changed"

Examples:  
git commit -m "Restructure folder layout for CloudFront function"  
git commit -m "Fix timestamp formatting logic"  
git commit -m "Add README for Git basics"

***

## 6. Push Your Branch to GitHub

Push your branch to the remote repository:

git push -u origin feature/your-branch-name

Future pushes:

git push

***

## 7. Open a Pull Request (PR)

Go to the repository:

<https://github.com/twdb/FloodScienceData-CloudFront>

Create a Pull Request:

From: your branch  
Into: main

Describe the changes you made.  
A reviewer will review and merge your PR.

***

## 8. Keep Your Branch Updated with Main (Optional but Recommended)

If changes were made in `main` after you created your branch, update your branch:

git switch main  
git pull  
git switch feature/your-branch-name  
git pull --rebase origin main

***

## 9. Full Contributor Workflow Summary

1.  git clone <https://github.com/twdb/FloodScienceData-CloudFront.git>
2.  cd FloodScienceData-CloudFront
3.  git switch -c feature/my-branch
4.  (make changes)
5.  git add -A
6.  git commit -m "My update"
7.  git push -u origin feature/my-branch
8.  Open Pull Request → merge into main


