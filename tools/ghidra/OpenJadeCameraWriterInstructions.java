// Export bounded instruction evidence for camera field writes, read-only.
import ghidra.app.script.GhidraScript;
import java.nio.file.*;
public class OpenJadeCameraWriterInstructions extends GhidraScript {
 public void run() throws Exception {
  if (!"6587d499f4ea6d0895179f74487045bc2c82a9d4e08a0a5046c1fb88ee3b6ec9".equalsIgnoreCase(currentProgram.getExecutableSHA256())) throw new Exception("Hash mismatch");
  StringBuilder out=new StringBuilder();
  for(long base:new long[]{0x483cd0L,0x67bb50L,0x693f20L,0x693620L,0x6d6cd0L}){
   out.append("START ").append(Long.toHexString(base)).append("\n");
   var at=toAddr(base);
   for(int i=0;i<120;i++){var ins=getInstructionAt(at);if(ins==null)break;out.append(at).append(" ").append(ins).append("\n");at=ins.getMaxAddress().add(1);}
  }
  Files.writeString(Paths.get(getScriptArgs()[0]),out.toString());
 }
}
