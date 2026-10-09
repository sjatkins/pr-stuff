#!/bin/bash
# Full backup of live/lib: everything the game persists (players, accounts,
# world saves, lockers, boards, builder files, admin lists), minus logs,
# cores and earlier tarballs. Uploaded to S3; nothing is kept on the host.
#
# PR_HOME is the directory that holds live/ and scripts/.
# Defaults to the current directory, so run from that directory or export it.
# The upload uses the instance role on the production host (no credentials
# on disk). Set PR_BACKUP_BUCKET to "" to skip the upload, for example on a
# dev machine; the tarball is then left in the temporary directory and its
# path printed.
PR_HOME="${PR_HOME:-$(pwd)}"
PR_BACKUP_BUCKET="${PR_BACKUP_BUCKET-pr-full-backup}"
PR_BACKUP_REGION="${PR_BACKUP_REGION:-us-west-1}"

work_dir="$(mktemp -d)"
backup_file="$work_dir/full_backup_$(date +%F).tar.gz"
minimum_size=5000k            # a real full backup is far larger than this

if ! tar --exclude="*.tgz" --exclude="*.tar.gz" --exclude="core.*" --exclude="logs" \
         -czf "$backup_file" -C "$PR_HOME/live" lib; then
  echo "backup_full: tar failed" >&2
  exit 1
fi

if ! test -n "$(find "$backup_file" -size +$minimum_size)"; then
  echo "backup_full: $backup_file is smaller than $minimum_size; not uploading" >&2
  exit 1
fi

if test -z "$PR_BACKUP_BUCKET"; then
  echo "backup_full: no bucket set; tarball left at $backup_file"
  exit 0
fi

if ! aws s3 cp --region "$PR_BACKUP_REGION" --only-show-errors \
       "$backup_file" "s3://$PR_BACKUP_BUCKET/"; then
  echo "backup_full: upload of $backup_file to s3://$PR_BACKUP_BUCKET/ failed; tarball left there" >&2
  exit 1
fi

rm -rf "$work_dir"
