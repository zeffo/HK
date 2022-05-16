-- DropForeignKey
ALTER TABLE "PlaylistTrack" DROP CONSTRAINT "PlaylistTrack_playlistId_fkey";

-- AddForeignKey
ALTER TABLE "PlaylistTrack" ADD CONSTRAINT "PlaylistTrack_playlistId_fkey" FOREIGN KEY ("playlistId") REFERENCES "Playlist"("id") ON DELETE CASCADE ON UPDATE CASCADE;
